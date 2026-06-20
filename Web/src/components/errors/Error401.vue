<template>
  <section class="error-page">
    <h2>401 未授权</h2>
    <p>您需要先登录才能访问此页面。</p>
    <RouterLink to="/login" class="primary-button">去登录</RouterLink>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>
