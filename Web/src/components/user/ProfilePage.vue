<template src="./ProfilePage.html"></template>

<script src="./ProfilePage.js"></script>

<style scoped>
.profile-page {
  position: relative;
  display: grid;
  gap: 18px;
  max-width: 720px;
}

.profile-loading {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.72);
  backdrop-filter: blur(1px);
}

.profile-loading-box {
  padding: 12px 18px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #ffffff;
  color: #1d4ed8;
  font-size: 1em;
  font-weight: 700;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.12);
}

.profile-page h2 {
  margin: 0;
}

.profile-form,
.profile-meta {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 18px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
}

.profile-form {
  display: grid;
  gap: 14px;
}

.profile-form label {
  display: grid;
  gap: 6px;
  color: #475569;
  font-size: 1em;
}

.profile-form input,
.profile-form select,
.profile-form textarea {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 10px 11px;
  font: inherit;
}

.profile-form textarea {
  resize: vertical;
}

.primary-button {
  width: fit-content;
  border: 0;
  border-radius: 6px;
  padding: 10px 14px;
  background: #2563eb;
  color: #ffffff;
  cursor: pointer;
  font: inherit;
}

.primary-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.info-message {
  width: fit-content;
  margin: 0;
  padding: 10px 12px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1d4ed8;
}

.profile-meta {
  display: grid;
  gap: 8px;
  color: #475569;
}

.profile-meta p {
  margin: 0;
}
</style>
