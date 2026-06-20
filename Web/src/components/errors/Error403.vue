<template>
  <section class="error-page">
    <h2>403 禁止访问</h2>
    <p>您当前的账号权限不足，无法访问该页面。</p>
    <RouterLink to="/dashboard" class="primary-button">返回首页</RouterLink>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
