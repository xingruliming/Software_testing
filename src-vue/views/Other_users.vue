<template>
  <div >
    <el-table :data="tableData" stripe style="width: calc(100vw - 150px)" border>
      <el-table-column prop="username" label="用户名"  />
      <el-table-column prop="identity" label="身份"  />
      <el-table-column prop="nickName" label="昵称" />
      <el-table-column prop="age" label="年龄" />
      <el-table-column prop="sex" label="性别" />
      <el-table-column prop="address" label="地址" />
      <el-table-column v-if="identity === '企业'" fixed="right" label="邀请" min-width="50">
        <template #default="scope">
          <el-button type="success" :icon="Message" circle @click="invite(scope.row)" />
        </template>
      </el-table-column>
    </el-table>
    <div  style="margin: 10px 0">
      <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[5,10,20]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
      />
    </div>
  </div>

</template>


<script>
import {request} from "@/utils/request";
import {mapGetters} from "vuex";
import {Message} from "@element-plus/icons-vue";

export default {
  name: "Other_users",
  computed: {
    Message() {
      return Message
    },
      ...mapGetters(['getIdentity','getUsername','getId']),  // 获取身份的 getter
      identity() {
        return this.getIdentity;  // 将身份赋值给 identity
      },
      name(){
        return this.getUsername;
      },
      id(){
        return this.getId;
      }
  },

  data() {
    return {
      form: {},
      tableData: [],
      currentPage: 1,
      pageSize: 10,
      total: 10,
    }
  },
  created(){
    this.load()
  },
  methods: {
    load() {
      request.get("/home/user", {
        params: {
          pageNum: this.currentPage,
          pageSize: this.pageSize,
          search: this.search
        }
      }).then(res => {
        console.log(res)
        const existingUsernames = this.getUsername
        console.log(existingUsernames)
        this.tableData = res.data.records.filter(record =>
            record.username !== existingUsernames && record.identity !== "管理员"
        );
        console.log(this.tableData)
        this.total = res.data.total
      })
    },
    handleCurrentChange(pageNum) { //改变当前页码触发
      this.currentPage = pageNum;
      this.load();
    },
    handleSizeChange(pageSize) { //改变当前每页的个数触发
      this.pageSize = pageSize;
      this.load();
    },
    invite(row){
      const params = {
        userId : row.id,
        companyId : this.id,
        state : "invited",
        companyName:this.name,
      }
      request.post("/company/user/", params).then(res =>{
          console.log(res);
          if(res.code === '0'){
            this.$message.success("邀请已发送!");
          }
          else{
            this.$message.warning(res.msg);
          }
      })
    }
  }

}
</script>

<style scoped>

</style>