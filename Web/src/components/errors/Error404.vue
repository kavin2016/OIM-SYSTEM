<template>
  <section class="error-page">
    <h2>404 页面不存在</h2>
    <p>抱歉，您访问的页面不存在或已被移除。</p>
    <RouterLink to="/dashboard" class="primary-button">返回首页</RouterLink>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
