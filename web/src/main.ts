/**
 * 应用入口：挂载 Pinia + Vue Router + Ant Design Vue
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'

import App from './App.vue'
import router from './router'
import './assets/styles/global.css'
// Yuxi v0.7.0 工作台基座样式（plain CSS，不引入 Less）。
// 详见 docs/THIRD_PARTY_NOTICES.md。
import './assets/styles/yuxi/index.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(Antd)
app.mount('#app')
