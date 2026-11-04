import { ref } from 'vue'

// Shared open state so header/footer/tab-bar entry points can open the single DemoSettings dialog.
export const demoSettingsOpen = ref(false)
export const openDemoSettings = () => {
  demoSettingsOpen.value = true
}
export const closeDemoSettings = () => {
  demoSettingsOpen.value = false
}
