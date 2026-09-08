<template>
  <div class="demand-container">
    <el-scrollbar class="demand-list">
      <el-card v-for="(demand, index) in demands" :key="index" class="demand-card" :style="{ minHeight: '300px' }">
        <div class="card-content">
          <h3 v-html="demand.title" style="margin-bottom: 10px"></h3>
          <p v-html="truncatedContent(demand.content)" style="margin-bottom: 10px"></p>
          <el-button type="text" @click="goToDetail(demand)">查看详情 >></el-button>
          <div class="demand-footer">
            <span>发布时间 {{ demand.date }}</span>
          </div>
        </div>
      </el-card>
    </el-scrollbar>
  </div>
</template>


<script>
import '@/assets/css/global.css'
import {request} from "@/utils/request";
import {mapGetters} from "vuex";
export default {
  name:"Requirement",
  data() {
    return {
      demands:[],

    };
  },
  computed: {
    ...mapGetters(['getIdentity','getId']),  // 获取id的 getter
    user_id() {
      return this.getId;  //
    },
    user_identity() {
      return this.getIdentity;
    }
  },
  beforeRouteEnter(to, from, next) {
    next(vm => {
      vm.load(); // 在进入路由时加载数据
    });
  },

  methods: {
    load(){
      const isCompany = this.user_identity === '企业'; // 判断是否为企业用户，假设企业用户的身份标识是 'company'
      const state = this.$route.path.includes('requirement') ? '已发布' : '未发布'; // 根据路由判断状态
      if(isCompany){
        request.get('/company/requirement',{
          params:{
            state:state,
            userId:this.user_id,
          }
        }).then(res => {
          console.log(res);
          if(res.code === '0'){
            this.demands = res.data
          }
          else{
            if(res.code === '-1') {
              this.$message.error('不存在发布的需求！');
            }
            else{
              this.$message.error('不存在保存的需求！');
            }
            this.demands = res.data
          }
        })
      }
      else{
        request.get('/client/requirement', {
          params: {
            state: '已发布'
          }
        }).then(res => {
          console.log(res);
          if (res.code === '0') {
            this.demands = res.data;
          } else {
            this.$message.error('未存在发布的需求！');
          }
        });
      }
    },
    truncatedContent(content) {
      if(content.length > 80){
        return content.substring(0,80) + '...';
      }
      return content; // 否则返回原内容
    },

    goToDetail(demand) {
      const path = demand.state === '已发布'
          ? '/company/requirement/detail'
          : '/company/draft/detail'; // 根据状态选择跳转路径

      console.log("跳转到需求详情页，ID:", demand.id, "状态:", demand.state);
      // 作为查询参数传递 ID 和 state
      this.$router.push({ path, query: { id: demand.id, state: demand.state } });
    }
  }
};
</script>

<style scoped>

</style>
