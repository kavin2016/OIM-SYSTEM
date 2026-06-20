<template>
  <div class="hello-card">
    <h2>{{ msg }}</h2>
    <p>编辑 <code>src/App.vue</code> 来开始构建你的页面。</p>
  </div>
</template>

<script setup>
import '../styles/components/hello-world.css'

const props = defineProps({
  msg: String
})
</script>
