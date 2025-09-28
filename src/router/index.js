import { createRouter, createWebHistory } from 'vue-router'
import ScriptExecution from '../views/ScriptExecution.vue'
import ExecutionHistory from '../views/ExecutionHistory.vue'
import AgentManagement from '../views/AgentManagement.vue'

const routes = [
  {
    path: '/',
    redirect: '/script-execution'
  },
  {
    path: '/script-execution',
    name: 'ScriptExecution',
    component: ScriptExecution
  },
  {
    path: '/execution-history',
    name: 'ExecutionHistory',
    component: ExecutionHistory
  },
  {
    path: '/agent-management',
    name: 'AgentManagement',
    component: AgentManagement
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
