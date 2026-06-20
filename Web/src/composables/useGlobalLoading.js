import { computed, ref } from 'vue'

const pendingRequests = ref(0)

const globalLoading = computed(() => pendingRequests.value > 0)

function startGlobalLoading() {
  pendingRequests.value += 1
}

function stopGlobalLoading() {
  pendingRequests.value = Math.max(0, pendingRequests.value - 1)
}

export { globalLoading, startGlobalLoading, stopGlobalLoading }
