import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../manager/HomeView.vue'
import Layout from "@/layout/Layout.vue";
import Login from "@/views/Login.vue";
import Register from "@/views/Register.vue";
import Announcement from "@/company/Announcement.vue";
import Client_announcement from "@/user/Client_announcement.vue";
import Other_users from "@/views/Other_users.vue";
import Person from "@/views/Person.vue";
import Requirement from "@/company/Requirement.vue";
import Publish_requirement from "@/company/Publish_requirement.vue";
import Detail_requirement from "@/company/Detail_requirement.vue";
import Reply from "@/user/Reply.vue";
import file from "@/manager/file.vue";


const routes = [
  {
    path: '/',
    redirect: '/login' // 将根路径重定向到登录页
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },

  {
    path: '/home',
    name: 'Layout',
    component: Layout,
    children: [
      {
        path: 'user',
        name: 'HomeView',
        component: HomeView
      },
      {
        path: 'announcement',
        name: 'Announcement',
        component: Announcement
      },
      {
        path: 'file',
        name:'file',
        component: file
      }
    ]
  },
  {
    path: '/register',
    name:'Register',
    component: Register
  },
  {
    path: '/client',
    name:'Layout2',
    component: Layout,
    children: [
      {
        path: 'announcement',
        name: 'Client_announcement',
        component: Client_announcement
      },
      {
        path:'requirement',
        name:'requirement',
        component:Reply,
      },
      {
        path:'star',
        name:'star',
        component:Reply,
      },
      {
        path:'detail',
        name:'Detail_requirement',
        component:Detail_requirement,
      },
      {
        path:'users',
        name:'Other_users',
        component:Other_users,
      },
      {
        path: 'personal',
        name:'Client_person',
        component: Person
      },
    ]
  },
  {
    path:'/company',
    name:'Logout_company',
    component: Layout,
    children: [
      {
        path:'users',
        name:'Other_users_2',
        component:Other_users,
      },
      {
        path: 'personal',
        name:'Company_person',
        component: Person,
      },
      {
        path: 'publish',
        name:'Publish_requirement',
        component: Publish_requirement,
      },
      {
        path: 'requirement',
        name: 'requirement2',
        component: Requirement,
      },
      {
        path:'requirement/detail',
        name:'Detail_requirement2',
        component:Detail_requirement,
      },
      {
        path:'draft',
        name:'requirement3',
        component: Requirement,
      },
      {
        path:'draft/detail',
        name:'Detail_requirement3',
        component:Detail_requirement,
      },
      {
        path: 'reply',
        name:'reply_company',
        component: Reply,
      },
      {
        path: 'file',
        name:'file2',
        component: file
      },
      {
        path: 'announcement',
        name: 'Client_announcement_2',
        component: Client_announcement
      },
    ]
  }


]


const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router
