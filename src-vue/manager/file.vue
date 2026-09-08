<template>
  <div>
    <el-table :data="fileList" stripe style="width: calc(100vw - 150px)" border>
      <el-table-column prop="username" label="上传用户" min-width="30"/>
      <el-table-column prop="demandname" label="针对需求" />
      <el-table-column prop="filename" label="文件名" />
      <el-table-column prop="filesize" label="文件大小" min-width="30" :formatter="formatFileSize"/>

      <el-table-column fixed="right" label="操作" min-width="30">
        <template #default="scope">
          <el-button
              v-if="identity === '管理员' "
              type="primary"
              @click="downloadFile(scope.row.fileid)"
          >
            下载
          </el-button>

          <el-button
              v-if="identity === '企业' && scope.row.pass === 'true'"
              type="primary"
              @click="downloadFile(scope.row.fileid)"
          >
            下载
          </el-button>

          <el-button
              v-if="identity === '管理员' && scope.row.pass === 'false'"
              type="primary"
              @click="passFile(scope.row.id)">
              通过
          </el-button>
          <!-- 如果文件已经通过，则显示绿色的“已通过”标签 -->
          <el-tag
              v-if="identity === '管理员' && scope.row.pass === 'true'"
              type="success"
              size="large"
              style="margin-left:12px; font-size: 13px; font-weight: bold; background-color: #67C23A; color: white; padding: 2px 9px;">
              已通过
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>


<script>
import {request} from "@/utils/request";
import {mapGetters} from "vuex";

export default {
  name: "file",
  data() {
    return {
      fileList: []  // 用于存储文件列表
    };
  },
  computed: {
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
  beforeRouteEnter(to, from, next) {
    next(vm => {
      vm.load(); // 在进入路由时加载数据
    });
  },
  methods:{
    formatFileSize(row, column, cellValue, index) {
      if (cellValue < 1024) {
        return `${cellValue} B`; // 小于1KB
      } else if (cellValue < 1024 * 1024) {
        return `${(cellValue / 1024).toFixed(2)} KB`; // 小于1MB
      } else {
        return `${(cellValue / 1024 / 1024).toFixed(2)} MB`; // 大于1MB
      }
    },
    load(){
      request.get(`/upload?identity=${this.identity}&id=${this.id}` ).then(res =>{
        console.log(res);
        this.fileList = res.data;
      })
    },
    downloadFile(fileId) {
      // 构建文件下载链接
      const url = `/api//upload/${fileId}`;
      // 创建一个隐藏的链接并点击它以触发下载
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute("download", ""); // 提示下载
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    passFile(Id){
      request.put("/upload/" + Id).then(res =>{
            console.log(res);
            if(res.code === '0'){
              this.$message.success("成功通过！");
              this.load();
            }
            else{
              this.$message.error(res.msg);
            }
      })
    }

  }

}

</script>



<style scoped>

</style>