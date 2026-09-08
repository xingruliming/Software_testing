<template>
  <div style="height: 50px; line-height: 50px; border-bottom: 1px solid #ccc; display: flex; align-items: center;">
    <div style="width: 200px; padding-left: 40px; font-weight: bold; font-size: 30px; color: cornflowerblue;">
      {{ identity === '管理员' ? '后台管理' : identity === '用户' ? '开发人员' : '企业' }}
    </div>
    <div style="flex: 1 ; display: flex; justify-content: flex-end; margin-right: 30px">

      <!-- 状态栏提示 -->
      <el-tooltip v-if="invitations.length > 0 && identity === '用户'" content="点击查看邀请" placement="top-start">
        <el-badge :value="invitations.length" max="99" class="item" :offset="[10, 15]">
          <el-button type="primary" @click="handleViewInvitations">
            企业邀请
          </el-button>
        </el-badge>
      </el-tooltip>

    </div>

    <div style="width: 150px">
      <el-dropdown trigger="click">
        <span class="el-dropdown-link" style="font-size: 17px;margin-top: 12px">
          {{ getUsername }}
          <el-icon class="el-icon--right">
            <ArrowDown />
          </el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="exit">退出系统</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>

  <el-dialog v-model="dialogTableVisible" title="企业邀请" width="500">
    <el-table :data="invitations">
      <el-table-column prop="companyName" label="邀请者" width="300" />
      <el-table-column fixed="right" label="选择" header-align="center">
        <template #default="scope">
          <el-button type="success" @click="select('accepted',scope.row)">接受</el-button>
          <el-button type="danger" @click="select('rejected',scope.row)">拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>

</template>

<script>
import { ArrowDown } from '@element-plus/icons-vue';
import '@/assets/css/global.css';
import { mapGetters, mapActions } from 'vuex';
import {request} from "@/utils/request";

export default {
  name: "Header",
  components: { ArrowDown },
  computed: {
    ...mapGetters(['getId', 'getIdentity','getUsername']),  // 获取用户名和身份的 getter
    identity() {
      return this.getIdentity;  // 将身份赋值给 identity
    },
    id(){
      return this.getId;
    }
  },
  data() {
    return {
      invitations: [],  // 用于存储从后端获取的邀请信息
      dialogTableVisible:false,
      gridData:[],
    };
  },
  mounted() {
    this.fetchInvitationDetails();
  },
  methods: {
    ...mapActions(['logout']),  // 调用 Vuex 的 logout action
    exit() {
      this.logout();  // 退出并重置用户名
      this.$router.push('/login');  // 跳转回登录页面
    },
    fetchInvitationDetails(){
      request.get("/home/" + this.id).then(res =>{
        console.log(res.data);
        this.invitations = res.data;
      })
    },
    handleViewInvitations(){
      this.dialogTableVisible = true;
      console.log(this.invitations)
    },
    select(option,row){
      row.state = option;
      request.put("/home",row).then(res =>{
        console.log(res);
        if(option === "accepted"){
          this.$message.success("接受邀请！");
        }
        else{
          this.$message.error("拒绝邀请！");
        }
      })
      this.dialogTableVisible = false;
    }
  }
}
</script>



