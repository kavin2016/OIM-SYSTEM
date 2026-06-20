<template src="./DashboardHome.html"></template>

<script src="./DashboardHome.js"></script>

<style scoped>
.dashboard-home {
  display: grid;
  gap: 18px;
}

.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.dashboard-home h2,
.dashboard-home p {
  margin: 0;
}

.dashboard-summary {
  padding: 16px 18px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
}

.stat-label {
  font-size: 0.875em;
  color: #64748b;
  margin-bottom: 0.5em;
}

.stat-value {
  font-size: 1.5em;
  font-weight: bold;
  color: #0f172a;
  margin-bottom: 0.5em;
}

.stat-meta {
  font-size: 0.75em;
  color: #94a3b8;
}
</style>
