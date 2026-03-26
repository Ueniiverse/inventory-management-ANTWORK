<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="budget-section">
      <div class="budget-card">
        <label class="budget-label">{{ t('restocking.budgetLabel') }}</label>
        <div class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</div>
        <input
          type="range"
          min="1000"
          max="100000"
          step="1000"
          v-model.number="budget"
          class="budget-slider"
        />
        <div class="budget-range-labels">
          <span>{{ currencySymbol }}1,000</span>
          <span>{{ currencySymbol }}100,000</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ recommendations ? recommendations.total_cost.toLocaleString() : 0 }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ recommendations ? recommendations.remaining_budget.toLocaleString() : 0 }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.itemsSelected') }}</div>
          <div class="stat-value">{{ recommendations ? recommendations.items.length : 0 }}</div>
        </div>
      </div>

      <div class="card" v-if="recommendations && recommendations.items.length > 0">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.title') }} ({{ recommendations.items.length }})</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.demandGap') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations.items" :key="item.item_sku">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.demand_gap }}</td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toLocaleString() }}</td>
                <td>{{ item.quantity }}</td>
                <td><strong>{{ currencySymbol }}{{ item.line_cost.toLocaleString() }}</strong></td>
                <td>
                  <span :class="['badge', getLeadTimeBadge(item.quantity)]">
                    {{ t('restocking.days', { days: getLeadTimeDays(item.quantity) }) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="order-actions">
          <button
            class="place-order-btn"
            :disabled="orderPlaced || !recommendations || recommendations.items.length === 0"
            @click="placeOrder"
          >
            {{ t('restocking.placeOrder') }}
          </button>
          <p v-if="orderSuccess" class="order-success-msg">{{ t('restocking.orderSuccess') }}</p>
          <p v-if="orderError" class="order-error-msg">{{ orderError }}</p>
        </div>
      </div>

      <div v-else class="no-recommendations">
        {{ t('restocking.noRecommendations') }}
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const error = ref(null)
    const budget = ref(10000)
    const recommendations = ref(null)
    const orderPlaced = ref(false)
    const orderSuccess = ref(false)
    const orderError = ref(null)

    let debounceTimer = null

    const loadRecommendations = async () => {
      try {
        loading.value = true
        error.value = null
        orderSuccess.value = false
        orderError.value = null
        recommendations.value = await api.getRestockingRecommendations(budget.value)
      } catch (err) {
        error.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    watch(budget, () => {
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        orderPlaced.value = false
        loadRecommendations()
      }, 300)
    })

    // Clean up debounce timer on component unmount to prevent memory leaks
    onBeforeUnmount(() => {
      if (debounceTimer) clearTimeout(debounceTimer)
    })

    const getLeadTimeDays = (quantity) => {
      if (quantity < 100) return 7
      if (quantity <= 500) return 14
      return 21
    }

    const getLeadTimeBadge = (quantity) => {
      if (quantity < 100) return 'success'
      if (quantity <= 500) return 'warning'
      return 'danger'
    }

    const placeOrder = async () => {
      try {
        orderError.value = null
        orderSuccess.value = false
        const orderData = {
          items: recommendations.value.items.map(item => ({
            item_sku: item.item_sku,
            item_name: item.item_name,
            quantity: item.quantity,
            unit_cost: item.unit_cost
          })),
          total_value: recommendations.value.total_cost
        }
        await api.submitRestockingOrder(orderData)
        orderPlaced.value = true
        orderSuccess.value = true
      } catch (err) {
        orderError.value = t('restocking.orderError') + ': ' + err.message
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      loading,
      error,
      budget,
      recommendations,
      orderPlaced,
      orderSuccess,
      orderError,
      currencySymbol,
      getLeadTimeDays,
      getLeadTimeBadge,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-section {
  margin-bottom: 1.5rem;
}

.budget-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 480px;
}

.budget-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-value {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 1rem;
}

.budget-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.budget-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 3px;
}

.budget-slider::-moz-range-track {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
}

.budget-range-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #94a3b8;
}

.order-actions {
  padding: 1rem 1.5rem 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.order-success-msg {
  color: #16a34a;
  font-weight: 600;
  margin: 0;
}

.order-error-msg {
  color: #dc2626;
  font-weight: 600;
  margin: 0;
}

.no-recommendations {
  text-align: center;
  padding: 3rem 1rem;
  color: #64748b;
  font-size: 1rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}
</style>
