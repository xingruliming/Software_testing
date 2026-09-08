<template>
  <div>
    <el-menu
        default-active="1"
        class="el-menu-vertical-demo"
        style="min-height: calc(100vh - 50px); width: 150px;"
    >

      <!-- 当身份为管理员时显示 系统管理 菜单 -->
      <template v-if="identity === '管理员'">
        <el-sub-menu index="1">
          <template #title>
            <el-icon><Location /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="userManagement" @click="goTo('home/user')">
            <el-icon><User /></el-icon>
            用户管理
          </el-menu-item>
          <el-menu-item index="announcementManagement" @click="goTo('home/announcement')">
            <el-icon><ChatDotRound /></el-icon>
            公告管理
          </el-menu-item>
          <el-menu-item index="file" @click="goTo('home/file')">
            <el-icon><Files /></el-icon>
            案例管理
          </el-menu-item>
        </el-sub-menu>

      </template>

      <!-- 当身份为用户时显示 浏览 和 信息 菜单 -->
      <template v-if="identity === '用户'">
        <el-sub-menu index="1">
          <template #title>
            <el-icon><Location /></el-icon>
            <span @click="goTo('client')">浏览</span>
          </template>
          <el-menu-item index="announcement" @click="goTo('client/announcement')">
            <el-icon><ChatLineSquare /></el-icon>
            公告栏
          </el-menu-item>
          <el-menu-item index="requirement" @click="goTo('client/requirement')">
            <el-icon><ChatDotRound /></el-icon>
            需求栏
          </el-menu-item>
          <el-menu-item index="star" @click="goTo('client/star')">
            <el-icon><Star /></el-icon>
            我的收藏
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="2">
          <template #title>
            <el-icon><Reading /></el-icon>
            <span>信息</span>
          </template>
          <el-menu-item index="personal" @click="goTo('client/personal')">
            <el-icon><Edit /></el-icon>
            个人信息
          </el-menu-item>
          <el-menu-item index="users" @click="goTo('client/users')">
            <el-icon><User /></el-icon>
            其他用户
          </el-menu-item>
        </el-sub-menu>

      </template>

      <template v-if="identity === '企业'">
        <el-sub-menu index="1">
          <template #title>
            <el-icon><Location /></el-icon>
            <span @click="goTo('company')">需求管理</span>
          </template>
          <el-menu-item index="publish_requirement" @click="goTo('company/publish')">
            <el-icon><ChatLineSquare /></el-icon>
            发布需求
          </el-menu-item>
          <el-menu-item index="change_requirement" @click="goTo('company/requirement')">
            <el-icon><Connection /></el-icon>
            变更需求
          </el-menu-item><el-menu-item index="draft" @click="goTo('company/draft')">
            <el-icon><ChatDotRound /></el-icon>
            草稿箱
          </el-menu-item>
          <el-menu-item index="lookup" @click="goTo('company/reply')">
            <el-icon><View /></el-icon>
            查看需求
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="2">
          <template #title>
            <el-icon><Files /></el-icon>
            <span>浏览查询</span>
          </template>
          <el-menu-item index="announcement" @click="goTo('company/announcement')">
            <el-icon><ChatLineSquare /></el-icon>
            公告栏
          </el-menu-item>
          <el-menu-item index="file" @click="goTo('company/file')">
            <el-icon><Search /></el-icon>
            案例查询
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="3">
          <template #title>
            <el-icon><Reading /></el-icon>
            <span>信息</span>
          </template>
          <el-menu-item index="personal" @click="goTo('company/personal')">
            <el-icon><Edit /></el-icon>
            企业信息
          </el-menu-item>
          <el-menu-item index="users" @click="goTo('company/users')">
            <el-icon><User /></el-icon>
            其他用户
          </el-menu-item>
        </el-sub-menu>

      </template>
    </el-menu>
  </div>
</template>

<script>
import {
  ChatDotRound,
  ChatLineSquare,
  Connection,
  Edit, Files,
  Location,
  Reading, Search,
  Star, UploadFilled,
  User,
  View
} from '@element-plus/icons-vue';
import { useRouter } from 'vue-router';
import { mapGetters } from 'vuex';

export default {
  name: "Aside",
  components: {
    Search,
    Files,
    UploadFilled,
    Star,
    View,
    Connection,
    ChatDotRound, ChatLineSquare, Edit, Location, Reading, User
  },
  computed: {
    ...mapGetters(['getIdentity']),  // 获取身份的 getter
    identity() {
      return this.getIdentity;  // 将身份赋值给 identity
    }
  },

  setup() {
    const router = useRouter();
    const goTo = (route) => {
      router.push(`/${route}`);
    };

    return {
      goTo,
    };
  }
}
</script>
