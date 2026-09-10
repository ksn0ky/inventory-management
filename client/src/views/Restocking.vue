<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budget') }}</h3>
        </div>
        <input
          type="range"
          min="0"
          max="500000"
          step="5000"
          v-model.number="budget"
          class="budget-slider"
        />
        <div class="budget-readout">{{ formatCurrency(budget, currentCurrency) }}</div>
        <div class="budget-line">
          {{ t('restocking.allocated') }}: {{ formatCurrency(allocatedTotal, currentCurrency) }}
          ·
          {{ t('restocking.remaining') }}: {{ formatCurrency(remaining, currentCurrency) }}
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommended') }} ({{ recommendations.length }})</h3>
        </div>
        <p v-if="recommendations.length === 0" class="no-data">{{ t('restocking.noneInBudget') }}</p>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.product') }}</th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.current') }}</th>
                <th>{{ t('restocking.table.forecast') }}</th>
                <th>{{ t('restocking.table.qty') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in recommendations" :key="r.sku">
                <td>{{ translateProductName(r.name) }}</td>
                <td><strong>{{ r.sku }}</strong></td>
                <td>{{ r.current }}</td>
                <td>{{ r.forecast }}</td>
                <td>{{ r.qty }}</td>
                <td>{{ formatCurrency(r.unitCost, currentCurrency) }}</td>
                <td>{{ formatCurrency(r.lineCost, currentCurrency) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <button
        class="place-order-btn"
        :disabled="!canPlaceOrder"
        @click="placeOrder"
      >
        {{ t('restocking.placeOrder') }}
      </button>

      <div v-if="submitError" class="error">{{ submitError }}</div>
      <div v-if="lastSubmittedOrder" class="success-banner">
        {{ t('restocking.orderPlaced', { orderNumber: lastSubmittedOrder.order_number, days: lastSubmittedOrder.lead_time_days }) }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(100000)
    const submitting = ref(false)
    const submitError = ref(null)
    const lastSubmittedOrder = ref(null)

    const loadForecasts = async () => {
      try {
        loading.value = true
        forecasts.value = await api.getDemandForecasts()
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const recommendations = computed(() => {
      const rows = forecasts.value
        .filter(f => f.trend === 'increasing')
        .map(f => ({
          sku: f.item_sku,
          name: f.item_name,
          unitCost: f.unit_cost,
          current: f.current_demand,
          forecast: f.forecasted_demand,
          qty: f.forecasted_demand - f.current_demand,
          lineCost: (f.forecasted_demand - f.current_demand) * f.unit_cost
        }))
        .sort((a, b) => b.qty - a.qty)

      const kept = []
      let runningTotal = 0
      for (const row of rows) {
        if (runningTotal + row.lineCost <= budget.value) {
          kept.push(row)
          runningTotal += row.lineCost
        } else {
          break
        }
      }
      return kept
    })

    const allocatedTotal = computed(() =>
      recommendations.value.reduce((sum, r) => sum + r.lineCost, 0)
    )

    const remaining = computed(() => budget.value - allocatedTotal.value)

    const canPlaceOrder = computed(() =>
      recommendations.value.length > 0 && !submitting.value
    )

    const placeOrder = async () => {
      const payload = {
        items: recommendations.value.map(r => ({
          sku: r.sku,
          name: r.name,
          quantity: r.qty,
          unit_price: r.unitCost
        })),
        total_value: allocatedTotal.value,
        budget: budget.value
      }

      submitting.value = true
      submitError.value = null
      try {
        lastSubmittedOrder.value = await api.createRestockOrder(payload)
      } catch (err) {
        submitError.value = 'Failed to submit order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      t,
      currentCurrency,
      translateProductName,
      formatCurrency,
      loading,
      error,
      budget,
      submitting,
      submitError,
      lastSubmittedOrder,
      recommendations,
      allocatedTotal,
      remaining,
      canPlaceOrder,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-slider {
  width: 100%;
  -webkit-appearance: none;
  appearance: none;
  background: transparent;
  margin: 0.5rem 0 1rem;
}

.budget-slider:focus {
  outline: none;
}

.budget-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2563eb;
  border: none;
  margin-top: -6px;
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #2563eb;
  border: none;
}

.budget-slider:focus::-webkit-slider-thumb {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.budget-slider:focus::-moz-range-thumb {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.budget-readout {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-line {
  margin-top: 0.5rem;
  color: #64748b;
  font-size: 0.938rem;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.success-banner {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.no-data {
  text-align: center;
  color: #94a3b8;
  padding: 2rem;
}
</style>
