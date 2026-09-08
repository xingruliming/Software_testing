<template>
  <div class="post-editor">
    <el-input
        v-model="title"
        placeholder="在这里写下主贴标题"
        class="title-input"
        clearable
    ></el-input>
    <el-button type="primary" class="save-button" @click="submitPost('未发布')">
      保存需求
    </el-button>
    <el-button type="primary" class="submit-button" @click="submitPost('已发布')">
      发布需求
    </el-button>

    <quill-editor
        ref="quillEditor"
        v-model="content"
        :options="editorOptions"
        :style="{ height: editorHeight }"
    ></quill-editor>


  </div>
</template>

<script>
import { QuillEditor } from '@vueup/vue-quill'; // 导入 Quill 编辑器
import "quill/dist/quill.snow.css";
import {request} from "@/utils/request"; // 导入 Quill 样式
import { mapGetters, mapActions } from 'vuex';
import '@/assets/css/global.css'
export default {
  name: "PublishRequirement",
  components: {
    QuillEditor // 使用 VueUp 的 Quill 编辑器
  },
  created(){
    console.log("id" + this.user_id)
  },
  computed: {
    ...mapGetters(['getId']),  // 获取id的 getter
    user_id() {
      return this.getId;  //
    }
  },
  data() {
    return {
      title: '', // 存储标题
      content: '', // 存储编辑器内容
      editorHeight: '78vh', // 你想要的高度
      editorOptions: {
        theme: 'snow', // 主题
        modules: {
          toolbar: [
            [{ header: [1, 2, false] }],
            ['bold', 'italic', 'underline'],
            ['clean'] // 清除格式
          ],
        },
      },
    };
  },
  methods: {
    submitPost(state) {
      console.log("标题:", this.title);
      if(!this.title){
        this.$message.error("请填标题!")
        return
      }
      // 处理发布逻辑，例如发送到服务器
      const contentHtml = this.$refs.quillEditor.getHTML();  // 获取 HTML 内容
      console.log("内容:", contentHtml); // 打印内容
      if(contentHtml === "<p><br></p>"){
        this.$message.error("请输入需求!")
        return
      }
      const currentTime = new Date();
      const formattedDate = `${currentTime.getFullYear()}-${(currentTime.getMonth() + 1).toString().padStart(2, '0')}-${currentTime.getDate().toString().padStart(2, '0')} ${currentTime.getHours().toString().padStart(2, '0')}:${currentTime.getMinutes().toString().padStart(2, '0')}:${currentTime.getSeconds().toString().padStart(2, '0')}`;
      console.log(formattedDate)
      const params = {
        content : contentHtml,
        title : this.title,
        state : state,
        userId : this.user_id,
        star : false,
      }
      if(state === "已发布"){
        params.date = formattedDate;
      }
      request.post("/company/publish",params).then(res => {
        if (res.code === '0' && state === "未发布") {
          this.$message.success('保存成功！');
          // 刷新数据表
          this.resetForm(); // 调用重置表单方法
        }
        else if (res.code === '0' && state === "已发布") {
          this.$message.success('发布成功！');
          // 刷新数据表
          this.resetForm(); // 调用重置表单方法
        }
        else {
          this.$message.error('标题重复！');
        }
      })
    },
    resetForm() {
      this.title = ''; // 重置标题
      this.$refs.quillEditor.setText(''); // 清空编辑器内容
    }
  },
};
</script>


<style scoped>
.post-editor {
  max-width: 80vw;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.title-input {
  width: 75%;
  margin-bottom: 20px;
}

.submit-button {
  width: 10%;
  background-color: #f57423;
  margin-bottom: 20px;
  margin-left: 10px;
  color: white; /* 设置文本颜色 */
}

.submit-button:hover {
  background-color: #e3431f; /* 悬停时的颜色 */
  color: white; /* 设置文本颜色 */
}

/* 点击状态 */
.submit-button:active {
  background-color: #f57423; /* 点击时保持颜色 */
}

.save-button {
  width: 10%;
  background-color: #23a4f5;
  margin-bottom: 20px;
  margin-left: 10px;
}

.save-button:hover {
  background-color: #1f7ae3; /* 悬停时的颜色 */
  color: white; /* 设置文本颜色 */
}
.save-button:active {
  background-color:  #23a4f5; /* 点击时保持颜色 */
}
</style>

