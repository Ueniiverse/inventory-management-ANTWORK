<template>
  <div class="app">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo-monogram">CC</div>
        <div class="logo-text">
          <h1>{{ t('nav.companyName') }}</h1>
          <span class="subtitle">{{ t('nav.subtitle') }}</span>
        </div>
      </div>
      <button class="sidebar-toggle" @click="toggleSidebar">
        <svg class="toggle-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 4l-6 6 6 6"/></svg>
      </button>
      <nav class="sidebar-nav">
        <router-link to="/" class="sidebar-link" :class="{ active: $route.path === '/' }" :title="sidebarCollapsed ? t('nav.overview') : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="7" height="7" rx="1"/><rect x="11" y="2" width="7" height="7" rx="1"/><rect x="2" y="11" width="7" height="7" rx="1"/><rect x="11" y="11" width="7" height="7" rx="1"/></svg>
          <span class="link-label">{{ t('nav.overview') }}</span>
        </router-link>
        <router-link to="/inventory" class="sidebar-link" :class="{ active: $route.path === '/inventory' }" :title="sidebarCollapsed ? t('nav.inventory') : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 6l8-4 8 4-8 4-8-4z"/><path d="M2 6v8l8 4V10"/><path d="M18 6v8l-8 4V10"/></svg>
          <span class="link-label">{{ t('nav.inventory') }}</span>
        </router-link>
        <router-link to="/orders" class="sidebar-link" :class="{ active: $route.path === '/orders' }" :title="sidebarCollapsed ? t('nav.orders') : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="2" width="14" height="16" rx="2"/><path d="M7 6h6M7 10h6M7 14h4"/></svg>
          <span class="link-label">{{ t('nav.orders') }}</span>
        </router-link>
        <router-link to="/spending" class="sidebar-link" :class="{ active: $route.path === '/spending' }" :title="sidebarCollapsed ? t('nav.finance') : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 16l4-4 4 2 4-6 4-2"/><path d="M2 18h16"/></svg>
          <span class="link-label">{{ t('nav.finance') }}</span>
        </router-link>
        <router-link to="/demand" class="sidebar-link" :class="{ active: $route.path === '/demand' }" :title="sidebarCollapsed ? t('nav.demandForecast') : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 14l5-5 4 4 7-9"/><path d="M14 4h4v4"/></svg>
          <span class="link-label">{{ t('nav.demandForecast') }}</span>
        </router-link>
        <router-link to="/restocking" class="sidebar-link" :class="{ active: $route.path === '/restocking' }" :title="sidebarCollapsed ? t('nav.restocking') : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 3v4h-4"/><path d="M4 17v-4h4"/><path d="M16 7a7 7 0 01-1 9.5M4 13a7 7 0 011-9.5"/></svg>
          <span class="link-label">{{ t('nav.restocking') }}</span>
        </router-link>
        <router-link to="/reports" class="sidebar-link" :class="{ active: $route.path === '/reports' }" :title="sidebarCollapsed ? 'Reports' : undefined">
          <svg class="link-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="10" width="3" height="8" rx="0.5"/><rect x="7" y="6" width="3" height="12" rx="0.5"/><rect x="12" y="2" width="3" height="16" rx="0.5"/></svg>
          <span class="link-label">Reports</span>
        </router-link>
      </nav>
    </aside>

    <div class="content-area" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <header class="top-bar">
        <FilterBar />
        <div class="top-bar-controls">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    const sidebarCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')

    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
      localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value)
    }

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      sidebarCollapsed,
      toggleSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  min-height: 100vh;
}

/* Sidebar */
.sidebar {
  width: 220px;
  min-height: 100vh;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s ease;
  z-index: 100;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 60px;
}

/* Sidebar logo area */
.sidebar-header {
  display: flex;
  align-items: center;
  padding: 1rem 1rem 0.75rem;
  gap: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  min-height: 56px;
}

.logo-monogram {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 0.813rem;
  flex-shrink: 0;
}

.logo-text {
  overflow: hidden;
  white-space: nowrap;
  transition: opacity 0.15s ease, width 0.2s ease;
}

.sidebar.collapsed .logo-text {
  opacity: 0;
  width: 0;
}

.logo-text h1 {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.2;
}

.logo-text .subtitle {
  font-size: 0.688rem;
  color: #94a3b8;
  font-weight: 400;
  display: block;
  border-left: none;
  padding-left: 0;
}

/* Toggle button */
.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  transition: color 0.15s ease;
}

.sidebar-toggle:hover {
  color: #475569;
}

.toggle-icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.sidebar.collapsed .toggle-icon {
  transform: rotate(180deg);
}

/* Sidebar nav */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0.5rem;
  gap: 0.125rem;
  flex: 1;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.875rem;
  border-radius: 8px;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  border-left: 3px solid transparent;
}

.sidebar-link:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.sidebar-link.active {
  color: #2563eb;
  background: #eff6ff;
  border-left-color: #2563eb;
}

.link-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.link-label {
  overflow: hidden;
  transition: opacity 0.15s ease;
}

.sidebar.collapsed .link-label {
  opacity: 0;
  width: 0;
}

/* Content area */
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  margin-left: 220px;
  transition: margin-left 0.2s ease;
}

.content-area.sidebar-collapsed {
  margin-left: 60px;
}

/* Top bar (replaces top-nav) */
.top-bar {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  min-height: 56px;
  position: sticky;
  top: 0;
  z-index: 90;
}

.top-bar-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-left: auto;
  flex-shrink: 0;
}

/* FilterBar is now inside top-bar, remove its own sticky behavior */
.top-bar .filters-bar {
  position: static;
  border-bottom: none;
  background: transparent;
  padding: 0;
  flex: 1;
}

.top-bar .filters-container {
  padding: 0;
  max-width: none;
}

.main-content {
  flex: 1;
  width: 100%;
  padding: 1.5rem 2rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: #64748b;
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: white;
  border-radius: 10px;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>
