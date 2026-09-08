<template>
  <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px">
    <div>
      <el-button style="margin-left: 20px" type="primary" @click="add">创建公告</el-button>
      <el-popconfirm title="确认发布吗?" @confirm="publishSelected">
        <template #reference>
          <el-button style="margin-left: 20px" type="primary">发布</el-button>
        </template>
      </el-popconfirm>
        <el-popconfirm title="确认删除吗?" @confirm="deleteSelected">
          <template #reference>
            <el-button style="margin-left: 20px" type="danger">删除</el-button>
          </template>
        </el-popconfirm>

    </div>
    <div style="margin-left: 20px">
      <el-select
          v-model="value"
          clearable
          placeholder="公告状态"
          style="width: 240px"
          @change="filterByStatus"
      >
        <el-option
            v-for="item in options"
            :key="item.value"
            :label="item.label"
            :value="item.value"
        />
      </el-select>
    </div>

    <el-table :data="tableData" stripe style="width: calc(100vw - 150px)"  :cell-class-name="getCellClass"  @selection-change="handleSelectionChange" border>
      <el-table-column type="selection" width="60" />
      <el-table-column prop="title" label="标题"  />
      <el-table-column prop="type" label="类型" />
      <el-table-column prop="state" label="状态" />
      <el-table-column prop="issuer" label="发布人" />
      <el-table-column prop="time" label="发布时间"  sortable/>
      <el-table-column
          prop="content"
          label="公告内容"
          show-overflow-tooltip
      />
      <el-table-column fixed="right" label="操作" min-width="55">
        <template #default="scope">
          <el-button type="text" @click="lookup(scope.row)">查看公告</el-button>
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

      <el-dialog v-model="dialogVisible" title="公告" width="40%" :style="{ maxHeight: '80vh' }" >
        <el-form :model="form"  ref="formRef" label-width="120px">
          <el-form-item label="标题">
            <el-input v-model="form.title" :disabled="isViewOnly" style="width: 85%"/>
          </el-form-item>
          <el-form-item label="类型">
            <el-input v-model="form.type" :disabled="isViewOnly" style="width: 85%"/>
          </el-form-item>
          <el-form-item label="发布者">
            <el-input v-model="form.issuer" :disabled="isViewOnly" style="width: 85%"/>
          </el-form-item>
          <el-form-item label="公告内容">
            <!-- 添加公告内容输入框 -->
            <el-input
                type="textarea"
                v-model="form.content"
                placeholder="请输入公告内容"
                style="width: 85% ; max-height: 300px; "
                :autosize="{ minRows: 5, maxRows: 15 }"
                :disabled="isViewOnly"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <div class="dialog-footer">
            <el-button v-if="isCreating" @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="save">确定</el-button>
          </div>
        </template>
      </el-dialog>


    </div>

  </div>
</template>


<script>
import {request} from "@/utils/request";
import moment from 'moment';
import {options} from "axios";
export default {
  name: "Announcement",
  components:{

  },
data() {
  return {
    form: {},
    dialogVisible: false,
    search: '',
    currentPage: 1,
    pageSize: 10,
    total: 10,
    tableData: [],
    selectedRows: [],
    isViewOnly: false, // 新增：查看模式标志
    isCreating: false, // 是否处于创建模式
    options: [ // 更新选项
      { label: '已发布', value: '已发布' },
      { label: '未发布', value: '未发布' }
    ],
    value: '' // 用于存储选择的值
  }
},
created(){
  this.load();
},

methods: {
  options,
  handleSelectionChange(selection) {
    this.selectedRows = selection;
  },
  deleteSelected() {
    if (this.selectedRows.length === 0) {
      this.$message.warning('请先选择要删除的公告！');
      return; // 如果没有选中项，则返回
    }
    const selectedIds = this.selectedRows.map(item => item.id); // 假设每个公告有一个唯一的 ID

    // 发起删除请求
    request.delete("/home/announcement", { data: selectedIds })
        .then(res => {
          if (res.code === '0') {
            this.$message.success('删除成功！');
            // 刷新数据表
            this.load();
          }
          else {
            this.$message.error('删除失败！');
          }
        })
        .catch(error => {
          console.error('删除请求出错:', error);
          this.$message.error('删除失败！');
        });

    this.selectedRows = []; // 清空选中项

  },
  publishSelected(){
    if (this.selectedRows.length === 0) {
      this.$message.warning('请先选择要发布的公告！');
      return; // 如果没有选中项，则返回
    }
    const selectedIds = this.selectedRows.map(item => item.id); // 假设每个公告有一个唯一的 ID

    request.put("/home/announcement", selectedIds )
    .then(res =>{
      if(res.code === '0'){
        this.$message.success('发布成功！'); // 成功反馈
        console.log(res)
        this.load()
      }
      else{
        this.$message.error(res.msg)
      }
    })
    this.selectedRows = []; // 清空选中项

  },
  load(){
    request.get("/home/announcement",{
      params:{
        pageNum: this.currentPage,
        pageSize: this.pageSize,
        state: this.value // 传递选择的状态
      }
    }).then(res =>{
      console.log(res)
      this.tableData=res.data.records
      this.total=res.data.total
    })
  },
  add() {
    this.dialogVisible = true
    this.isCreating = true; // 处于创建模式
    this.form = {}
  },
  save(){
    if(this.form.id){
      this.dialogVisible = false; // 隐藏对话框
      this.isViewOnly = false;
    }
    else{
      if (this.validateForm()) {
      this.form.state = "未发布";
      request.post("/home/announcement", this.form).then(res => {
        console.log(res);
        if(res.code === '0'){
          this.$message.success('创建成功！'); // 成功反馈
          this.dialogVisible = false; // 隐藏对话框

          this.load(); // 刷新数据表
        }
        else{
          this.$message.error('创建失败！');
        }

      });
    }
    }
  },
  validateForm() {

    if (!this.form.title) {
      this.$message.error('请输入标题');
      return false;
    }
    if (!this.form.type) {
      this.$message.error('请输入类型');
      return false;
    }


    if (!this.form.issuer) {
      this.$message.error('请输入发布者');
      return false;
    }


    return true; // 如果所有验证都通过，返回 true
  },
  handleCurrentChange(pageNum){ //改变当前页码触发
    this.currentPage=pageNum;
    this.load();
  },
  handleSizeChange(pageSize){ //改变当前每页的个数触发
    this.pageSize=pageSize;
    this.load();
  },
  getCellClass({ row, column }) {
    if (column.property === 'state') {
      return row.state === '未发布' ? 'unpublished' : 'published';
    }
    return '';
  },
  lookup(row){
    this.form = JSON.parse(JSON.stringify(row))
    this.isViewOnly = true; // 进入查看模式
    this.isCreating = false; // 处于查看模式
    this.dialogVisible=true;
  },
  filterByStatus() {
    // 根据选择的状态过滤数据
    this.load();
  }
},

}

</script>

<style scoped>

</style>