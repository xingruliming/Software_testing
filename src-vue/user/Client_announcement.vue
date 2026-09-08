<template>
  <div class="announcement-page">
    <!-- 左侧导航栏 -->
    <el-container>
        <!-- 搜索框 -->
        <el-header>
          <div class="search-bar">
            <el-input placeholder="请输入标题或关键字" v-model="searchTitle" class="input-title" style="width: 250px;"  clearable>
            </el-input>
            <el-date-picker
                v-model="selectedDate"
                type="date"
                placeholder="请选择发布日期"
                class="input-date"
            ></el-date-picker>
            <el-button type="primary" @click="search" class="input-button">查询</el-button>
            <el-button type="primary" @click="reset" class="input-button">重置</el-button>
          </div>
        </el-header>

      <el-main>
        <div style="display: flex; justify-content: space-between; width: 100%;">
          <!-- 左侧公告列表 -->
          <div style="flex: 1; margin-right: 20px;">
            <el-table
                :data="announcements"
                border
                @row-click="viewDetails"
                style="width: 100%;"
                :header-row-style="{ color: '#191970' }"
            >
              <el-table-column label="公告标题">
                <template #header>
                  <span>
                    <el-icon><Notification /></el-icon>
                    公告标题
                  </span>
                </template>
                <template #default="scope">
                  {{ scope.row.title }} <!-- 显示每行的公告标题 -->
                </template>
              </el-table-column>
              <el-table-column prop="issuer" label="发布者" />
              <el-table-column prop="time" label="发布时间" sortable/>
            </el-table>

            <div style="margin: 10px 0">
              <el-pagination
                  v-model:current-page="currentPage"
                  v-model:page-size="pageSize"
                  :page-sizes="[5, 10, 20]"
                  layout="total, sizes, prev, pager, next, jumper"
                  :total="total"
                  @size-change="handleSizeChange"
                  @current-change="handleCurrentChange"
              />
            </div>
          </div>

          <!-- 右侧公告详情 -->
          <div style="flex: 1;">
            <div
                class="announcement-details"
                v-if="selectedAnnouncement"
                style="padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px; overflow-y: auto; max-height: 500px;"
            >
              <h3 style="text-align: center;">{{ selectedAnnouncement.title }}</h3>
              <p><strong>发布部门:</strong> {{ selectedAnnouncement.issuer }}</p>
              <p><strong>发布时间:</strong> {{ selectedAnnouncement.time }}</p>
              <p><strong>公告类型:</strong> {{ selectedAnnouncement.type }}</p>
              <p><strong>内容:</strong> {{ selectedAnnouncement.content }}</p>
            </div>
            <div v-else class="no-selection" style="margin-left: 250px ; color: #888;">请选择公告以查看详情</div>
          </div>
        </div>
      </el-main>

    </el-container>
  </div>
</template>

<script>
import '@/assets/css/global.css'
import {request} from "@/utils/request";
import {Notification} from "@element-plus/icons-vue";
export default {
  name:'Client_announcement',
  components: {Notification},
  data() {
    return {
      searchTitle: '',
      selectedDate: null,
      announcements: [],
      selectedAnnouncement: null,
      currentPage: 1,
      pageSize: 10,
      total: 10,
      state:'已发布'
    };
  },
  created(){
    this.load();
  },
  methods: {
    load(){
      request.get("/client/announcement",{
        params:{
          pageNum: this.currentPage,
          pageSize: this.pageSize,
          state: '已发布'
        }
      }).then(res =>{
        console.log(res)
        this.announcements=res.data.records
        this.total=res.data.total
      })
    },
    search() {
      // 搜索功能的逻辑
      console.log('Searching for:', this.searchTitle, this.selectedDate);
      const formattedDate = this.selectedDate
          ? `${this.selectedDate.getFullYear()}-${(this.selectedDate.getMonth() + 1).toString().padStart(2, '0')}-${this.selectedDate.getDate().toString().padStart(2, '0')}`
          : null;

      const params = {
        pageNum: this.currentPage,
        pageSize: this.pageSize,
        state: '已发布',
      };
      if (this.searchTitle) {
        params.title = this.searchTitle; // 仅当标题存在时添加
      }

      if (formattedDate) {
        params.time = formattedDate; // 仅当日期存在时添加
      }

      console.log(params.time)
      // 发送请求到后端 API，根据关键字和日期查询公告
      request.get("/client/announcement", { params }).then(res => {
        console.log(res.data.records)
        this.announcements = res.data.records;
        this.total = res.data.total;
      });
    },
    reset() {
      // 重置搜索框的内容
      this.searchTitle = '';
      this.selectedDate = null;
      this.load();

    },
    viewDetails(row) {
      // 查看公告详情的逻辑
      console.log('Viewing details for:', row);
      this.selectedAnnouncement = row; // 将当前点击的行数据保存到 selectedAnnouncement 中
    },
    handleCurrentChange(pageNum){ //改变当前页码触发
      this.currentPage=pageNum;
      this.load();
    },
    handleSizeChange(pageSize){ //改变当前每页的个数触发
      this.pageSize=pageSize;
      this.load();
    }
  },

};
</script>

<style scoped>

</style>
