<template>
  <el-table :data="tableData" border style="width: 100%">
    <el-table-column type="expand">
      <template #default="props">
        <div class="element">
          <h2 class="requirement-title">需求</h2>
          <p v-html="props.row.content" class="content-text"></p> <!-- 添加类名 -->

          <div class="button-container">
            <el-button type="primary" @click="commentOnUser(props.row.demandId)" class="action-button">
              <el-icon style="margin-right: 5px;">
                <ChatDotRound />
              </el-icon>
              评论
            </el-button>

            <el-button type="primary" @click="openUploadDialog(props.row.demandId)" class="action-button" v-if="identity === '用户'">
              <el-icon style="margin-right: 5px; ">
                <UploadFilled />
              </el-icon>
              提交案例
            </el-button>
          </div>
        </div>

      </template>
    </el-table-column>
    <el-table-column label="标题" prop="title" />
    <el-table-column label="发布日期" prop="date" sortable />
    <el-table-column label="发布者" prop="publisher" />
    <el-table-column  v-if="identity === '用户'"   fixed="right" label="收藏" min-width="55">
      <template #default="props">
        <el-button link type="primary" @click="toggleFavorite(props.row)">
          <el-icon :style="{ color: props.row.star === 'true' || props.row.star === true ? 'red' : '' }" style="margin-left: 10px;">
            <Star />
          </el-icon>
        </el-button>
      </template>
    </el-table-column>

  </el-table>

  <!-- 评论对话框 -->
  <el-dialog v-model="dialogVisible" title="评论" >
    <!-- 已存在的评论列表 -->
    <el-table :data="comment" border style="margin-bottom: 20px;">
      <el-table-column prop="username" label="评论者" width="120"/>
      <el-table-column prop="reply" label="评论内容" />
      <el-table-column prop="date" label="评论日期" width="160" />
    </el-table>

    <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[5,10,20]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        style="margin-bottom: 20px"
    />
    <!-- 评论输入框 -->
    <el-form>
      <el-form-item>
        <el-input
            type="textarea"
            v-model="reply"
            placeholder="输入你的评论"
            :autosize="{ minRows: 3, maxRows: 5 }"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="submitComment" style="margin-left: auto; display: block;">提交评论</el-button>
      </el-form-item>
    </el-form>
  </el-dialog>


  <!-- 上传文件对话框 -->
  <el-dialog v-model="uploadDialogVisible" title="提交案例">
    <div class="upload-header">
      <h3 style="margin-bottom: 10px ; justify-content:  flex-end;"></h3>
      <el-alert
          type="info"
          title="请选择您要上传的文件"
          class="upload-alert"
          show-icon
      />
    </div>
    <el-upload
        class="upload-demo"
        action="/upload"
        :on-success="handleUploadSuccess"
        :auto-upload="false"
        :limit="5"
        :file-list="fileList"
        :on-exceed="handleExceed"
        @change="handleFileChange"
        :headers="headers"
    >
<!--   action="/upload"：

文件上传的接口地址，上传时文件会提交到 /upload。
:on-success="handleUploadSuccess"：

文件上传成功时的回调函数，通常用于处理返回的结果。
:auto-upload="false"：

默认情况下，选择文件后会自动上传。设置为 false 表示需要手动点击“上传”按钮后才会上传。
:limit="5"：

文件上传数量限制，最多可上传 5 个文件。
:file-list="fileList"：

绑定当前选中的文件列表，数据存储在 fileList 数组中。
:on-exceed="handleExceed"：

当上传文件数量超过限制时触发的回调函数。
@change="handleFileChange"：

文件列表发生变化时（如选择、删除文件）触发的回调函数。
:headers="headers"：

自定义 HTTP 请求头，通常用于添加认证信息等"   -->
      <el-button slot="trigger" type="primary" style="margin-top: 15px" >选择文件</el-button>
    </el-upload>
    <div class="upload-button">
      <el-button
          slot="upload"
          type="success"
          @click="uploadFile"
          :disabled="fileList.length === 0"
      >
        上传
      </el-button>
    </div>

  </el-dialog>

</template>

<script>
import {request} from "@/utils/request";
import {ChatDotRound, Star, UploadFilled} from "@element-plus/icons-vue";
import {mapGetters} from "vuex";

export default {
  name: "Reply",
  components: {UploadFilled, ChatDotRound, Star},
  computed: {
    ...mapGetters(['getId','getIdentity']),  // 获取id的 getter
    user_id() {
      return this.getId;  //
    },
    identity(){
      return this.getIdentity;
    }

  },
  data(){
    return{
      tableData:[],
      dialogVisible: false,
      currentPage: 1,
      pageSize: 5,
      total: 10,
      reply:'',
      comment:[],
      currentDemandId:0,
      uploadDialogVisible: false,  // 控制上传文件的对话框
      fileList: [], // 用于存储已选择的文件列表
      headers: {},
    }
  },
  beforeRouteEnter(to, from, next) {
    next(vm => {
      vm.load(); // 在进入路由时加载数据
    });
  },
  methods:{
    load(){
      const star = this.$route.path.includes('star')
      if(star){
        request.get("/company/reply",{
          params:{
            state:"已发布",
            star:"true",
            id:this.user_id,
          }
        }).then(res => {
          console.log(res);
          this.tableData = res.data;
        })
      }
      else{
        request.get("/company/reply",{
          params:{
            state:"已发布",
            id:this.user_id,
          }
        }).then(res => {
          console.log(res);
          this.tableData = res.data;
        })
      }

    },
    toggleFavorite(row){
      console.log(row); // 打印 row 值
      row.star = row.star === "false" ? "true" : "false"; // 如果是 "false"，变为 "true"，否则变为 "false"
      request.put("/company/reply",row).then(res => {

          if(res.data.star === "true"){
            console.log(res)
            this.$message.success('已收藏！'); // 成功反馈
            this.load();
          }
          else{
            this.load();
            this.$message.error; // 成功反馈
          }
      })
    },
    display(){
      request.get("/company/requirement/reply",{
        params:{
          demandId:this.currentDemandId,
          pageNum: this.currentPage,
          pageSize: this.pageSize,
        }}).then(res =>{
            console.log(res);
            this.comment = res.data.records;
            this.total=res.data.total
      })
    },
    commentOnUser(demandId){
        this.dialogVisible = true;
        this.currentDemandId = demandId; // 保存当前需求ID
        this.display();
    },
    submitComment(){
      const currentTime = new Date();
      const formattedDate = `${currentTime.getFullYear()}-${(currentTime.getMonth() + 1).toString().padStart(2, '0')}-${currentTime.getDate().toString().padStart(2, '0')} ${currentTime.getHours().toString().padStart(2, '0')}:${currentTime.getMinutes().toString().padStart(2, '0')}:${currentTime.getSeconds().toString().padStart(2, '0')}`;
      if(this.reply === ''){
        this.$message.error("空评论！");
        return;
      }
      const params = {
        userId:this.user_id,
        demandId:this.currentDemandId,
        date:formattedDate,
        reply:this.reply,
      }
      request.post("/company/requirement",params).then(res => {
          if(res.code === '0'){
            this.$message.success("评论成功!");
            this.reply = ''; // 清空输入框
            this.display();
          }
          else{
            this.$message.error("评论失败");
          }
      })
    },
    handleCurrentChange(pageNum){ //改变当前页码触发
      this.currentPage=pageNum;
      this.display();
    },
    handleSizeChange(pageSize){ //改变当前每页的个数触发
      this.pageSize=pageSize;
      this.display();
    },
    // 打开上传文件的对话框
    openUploadDialog(demandId) {
      this.uploadDialogVisible = true;
      this.currentDemandId = demandId;
    },
    handleFileChange(file, fileList) {
      console.log("文件列表更新：", fileList); // 每次文件更新时打印文件列表
      console.log("选择的文件：", file);
      // 在文件上传前检查文件是否已存在
      if (this.isFileDuplicate(file)) {
        this.$message.error("文件已上传，请选择不同的文件!");
        this.fileList = fileList.filter((f, index) => f.name !== file.name || index === fileList.lastIndexOf(file));
        return false; // 阻止上传
      }

      // 文件上传前的处理逻辑，例如检查文件大小等
      const isValid = file.size < 5 * 1024 * 1024; // 限制文件大小为5MB
      if (!isValid) {
        this.$message.error("文件大小不能超过 5MB!");
        this.fileList = fileList.filter(f => f.name !== file.name );
        return false; // 阻止上传
      }
      // 更新 fileList
      this.fileList = fileList;
      return true; // 允许上传

    },
    uploadFile() {
      console.log("上传按钮被点击");

      if (this.fileList.length === 0) {
        this.$message.error("请先选择文件!");
        return;
      }

      // 实际上传操作
      const formData = new FormData();
      this.fileList.forEach(file => {
        formData.append("files", file.raw);
      });

      // 添加其他数据
      formData.append("userId", this.user_id);
      formData.append("demandId", this.currentDemandId);

      formData.forEach((value, key) => {
        console.log(key, value);  // 输出每个键和对应的值
      });

      request.post("/upload", formData,)
          .then(res => {
            console.log(res)
            if(res.code === '0') {
              this.handleUploadSuccess(res, this.fileList);
            }
            else if(res.code === '-1'){
              this.$message.error(res.msg)
            }
            else if(res.code === '-2'){
              this.$message.error(res.msg)
            }
            else if(res.code === '-3'){
              this.$message.error(res.msg)
            }
            else if(res.code === '-4'){
              this.$message.error(res.msg)
            }
            else if(res.code === '-5'){
              this.$message.error(res.msg)
            }

          })

    },
    handleUploadSuccess(res, fileList) {
      console.log(fileList)
      this.$message.success("文件上传成功！");
      this.fileList = []; // 上传成功后清空文件列表
      this.uploadDialogVisible = false;
    },
    handleExceed(files, fileList) {
      // 当上传的文件超过5个时，给出提示
      this.$message.warning("最多只能上传 5 个文件！");
    },
    isFileDuplicate(file) {
      // 假设通过文件名来判断文件是否重复
      const uploadedFiles = this.fileList || [];
      console.log("已上传的文件：", uploadedFiles);
      return uploadedFiles.some(f => f.name === file.name);
    },
  },
}
</script>

<style scoped>
.element {
  background-color: #f9f9f9;
  border: 1px solid #e4e4e4;
  border-radius: 2px;
  margin-bottom: 2px;
  padding-top: 5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: hidden;
}

.requirement-title {
  font-size: 20px;
  color: #333;
  margin-bottom: 10px;
  text-align: center; /* 将文本居中 */
}

.button-container {
  display: flex;
  justify-content:  flex-end; /* 按钮容器靠右对齐 */
  gap: 10px; /* 按钮之间的间距 */
  margin-bottom: 10px; /* 添加一些顶部间距 */
  margin-right: 20px;
}

.action-button {
  background-color: #409EFF;
  border-color: #409EFF;
  color: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
  display: inline-flex;
  align-items: center;
}

.action-button:hover {
  background-color: #66b1ff; /* hover 时的颜色 */
}

.content-text {
  padding-left: 20px; /* 可选：左侧添加一些内边距 */
  padding-bottom: 20px;
}

.upload-button{
  text-align: right;
}

</style>