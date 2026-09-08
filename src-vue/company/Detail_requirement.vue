<template>
  <div class="post-editor">
    <div class="header">
      <el-input
          v-model="title"
          placeholder="在这里写下主贴标题"
          class="title-input"
          clearable
      ></el-input>

      <div v-if="isPublished">
        <el-popconfirm title="确认更改吗?" @confirm="saveChanges">
          <template #reference>
            <el-button type="primary" class="edit-button">更改需求</el-button>
          </template>
        </el-popconfirm>
        <el-popconfirm title="确认删除吗?" @confirm="deleteDemand">
          <template #reference>
            <el-button type="primary" class="cancel-button">删除需求</el-button>
          </template>
        </el-popconfirm>
        <el-button type="danger" class="cancel-button" @click="cancel">
          取消
        </el-button>
      </div>

      <div v-else>
        <el-popconfirm title="确认发布吗?" @confirm="publishDemand">
          <template #reference>
        <el-button type="primary" class="publish-button" >发布需求</el-button>
          </template>
        </el-popconfirm>
        <el-popconfirm title="确认删除吗?" @confirm="deleteDemand">
          <template #reference>
            <el-button type="primary" class="cancel-button">删除需求</el-button>
          </template>
        </el-popconfirm>
        <el-button type="danger" class="cancel-button" @click="cancel">
          取消
        </el-button>
      </div>
    </div>

    <quill-editor
        ref="quillEditor"
        v-model="content"
        :options="editorOptions"
        :style="{ height: editorHeight }"
    ></quill-editor>
  </div>
</template>

<script>
import {request} from "@/utils/request";
import { QuillEditor } from '@vueup/vue-quill';
import "quill/dist/quill.snow.css";
import { mapGetters } from 'vuex';
export default {
  name: "Detail_requirement",
  components: {
    QuillEditor
  },
  computed: {
    ...mapGetters(['getId']),
    user_id() {
      return this.getId;
    },
    isPublished() {
      return this.$route.query.state === '已发布';
    }
  },
  data() {
    return {
      title: '',
      content: '',
      editorHeight: '78vh',
      editorOptions: {
        theme: 'snow',
        modules: {
          toolbar: [
            [{ header: [1, 2, false] }],
            ['bold', 'italic', 'underline'],
          ],
        },
      },
    };
  },
  created() {
    this.load();
  },
  methods: {
    load(){
      this.postId = parseInt(this.$route.query.id, 10); // 确保 postId 为整数
      request.get('/company/requirement/detail',{
        params:{
          id:this.postId,
        }
      }).then(res => {
        console.log(res);
        if(res.code === '0'){
          this.title = res.data.title;
          this.content = res.data.content;
          // 使用 nextTick 确保 DOM 更新
          this.$nextTick(() => {
            this.$refs.quillEditor.setHTML(this.content); // 手动设置 Quill 编辑器的内容
          });
        }
        else{
          this.$message.error('未存在发布的需求！');
        }
      })
    },
    saveChanges() {
      const contentHtml = this.$refs.quillEditor.getHTML();
      if (!this.title || contentHtml === "<br>") {
        this.$message.error("请完整填写标题和内容！");
        return;
      }
      const params = {
        content: contentHtml,
        title: this.title,
        id: this.postId,
      };
      request.post("/company/requirement/detail", params).then(res => {
        if (res.code === '0') {
          this.$message.success('更改成功！');
          this.$router.push("/company/requirement");
        } else {
          this.$message.error('更改失败！');
        }
      })
    },
    publishDemand(){
      const currentTime = new Date();
      const formattedDate = `${currentTime.getFullYear()}-${(currentTime.getMonth() + 1).toString().padStart(2, '0')}-${currentTime.getDate().toString().padStart(2, '0')} ${currentTime.getHours().toString().padStart(2, '0')}:${currentTime.getMinutes().toString().padStart(2, '0')}:${currentTime.getSeconds().toString().padStart(2, '0')}`;
      const contentHtml = this.$refs.quillEditor.getHTML();
      if (!this.title || contentHtml === "<br>") {
        this.$message.error("请完整填写标题和内容！");
        return;
      }
      const params = {
        content: contentHtml,
        title: this.title,
        id: this.postId,
        state:"已发布",
        date:formattedDate,
        star : false,
      };
      request.post("/company/requirement/detail", params).then(res => {
        if (res.code === '0') {
          this.$message.success('发布成功！');
          this.$router.push("/company/requirement");
        } else {
          this.$message.error('发布失败！');
        }
      })
    },
    deleteDemand(){
      request.delete(`/company/requirement/detail/${this.postId}`).then(res => {
        if (res.code === '0') {
          this.$message.success('删除成功！');
          this.$router.push("/company/requirement");
        }
        else {
          this.$message.error('删除失败！');
        }
      })
    },
    cancel() {
      this.load(); // 重新加载数据，恢复到未更改之前的内容
    }
  }
}
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

.header {
  display: flex;
  align-items: center; /* 垂直居中 */
  margin-bottom: 2px; /* 与编辑器间距 */
}

.title-input {
  width: 75%;
  margin-bottom: 20px;
}

.edit-button {
  min-width:95px;
  margin-bottom: 20px;
  margin-left: 10px;
  color: white; /* 设置文本颜色 */
}

.publish-button {
  min-width:100px;
  margin-bottom: 20px;
  margin-left: 10px;
  color: white; /* 设置文本颜色 */
}
.cancel-button {
  min-width: 95px;
  margin-bottom: 20px;
  margin-left: 10px;
  background-color: #f57423;
  color: white; /* 设置文本颜色 */
}

.cancel-button {
  width: 10%;
  margin-bottom: 20px;
  margin-left: 10px;
  color: white; /* 设置文本颜色 */
}

.cancel-button:hover {
  background-color: #e3431f; /* 悬停时的颜色 */
  color: white; /* 设置文本颜色 */
}

/* 点击状态 */
.cancel-button:active {
  background-color: #f57423; /* 点击时保持颜色 */
}


</style>