<template>
  <div class="login-container">
    <div class="welcome-title">欢迎登录</div>
    <el-form ref="form" :model="form"   size="default" class = "login-form" :rules="rules">
      <el-form-item prop="username">
        <el-input v-model="form.username" :prefix-icon="User" />
      </el-form-item>
      <el-form-item prop="password">
        <el-input v-model="form.password"  :prefix-icon="Lock" show-password/>
      </el-form-item>
      <el-form-item >
        <el-radio-group v-model="form.identity" >
          <el-radio value="用户">用户</el-radio>
          <el-radio value="企业">企业</el-radio>
          <el-radio value="管理员">管理员</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item  >
        <el-button style="width: 250px " type="primary" @click="login">登录</el-button>
      </el-form-item>
      <el-form-item  >
         <el-button style="width: 250px" type="primary" @click="$router.push('/register')">注册</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import {request} from "@/utils/request";

export default {
  name: "Login",
  computed: {
    User() {
      return User
    },
    Lock(){
      return Lock
    }
  },
  data(){
    return {
      form: {},
      rules:{
        username:[
          {required:true,message:'请输入用户名',trigger:'blur'}
        ],
        password:[
          {required:true,message:'请输入密码',trigger:'blur',}
        ],

      }
    }
  },
  methods:{
    login(){
      request.post("/login",this.form).then(res =>{
        if(res.code === '0'){

          this.$store.commit('setUsername', this.form.username);  // 提交 mutation 更新用户名
          this.$store.commit('setIdentity', this.form.identity); // 提交 mutation 更新身份
          this.$store.commit('setId', res.data); // 提交 mutation 更新身份
          console.log(res.data)
          this.$message.success('登录成功！'); // 成功反馈
          switch (this.form.identity) {
            case '管理员':
              this.$router.push("/home"); // 管理员进入主页
              break;
            case '用户':
              this.$router.push("/client"); // 用户进入 /lll
              break;
            case '企业':
              this.$router.push("/company"); // 企业进入 /ooo
              break;
            default:
              this.$message.error('身份未知，无法跳转');
              break;
          }
        }
        else{
          this.$message.error(res.msg);
        }
      })
    },

  }
}
import '@/assets/css/global.css'
import {User} from '@element-plus/icons-vue'
import {Lock} from '@element-plus/icons-vue'
</script>