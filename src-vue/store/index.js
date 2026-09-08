import { createStore } from 'vuex';
import createPersistedState from 'vuex-persistedstate';  // 引入插件

export default createStore({
  state: {
    username: '', // 存储用户名
    identity: '', // 身份
    id:null,//id
  },
  getters: {
    getUsername: (state) => state.username, // 获取用户名的 getter
    getIdentity: (state) => state.identity,
    getId:(state)=> state.id,
  },
  mutations: {
    setUsername(state, username) {
      state.username = username; // 更新用户名
    },
    reset(state) {
      state.username = '';
      state.identity = ''; // 将用户名和身份重置为空
      state.id = null;
    },
    setIdentity(state, identity) {
      state.identity = identity;
    },
    setId(state, id){
      state.id = id;
}
  },
  actions: {
    updateUsername({ commit }, username) {
      commit('setUsername', username); // 通过 action 更新用户名
    },
    logout({ commit }) {
      commit('reset'); // 退出时重置用户名和身份
    }
  },
  modules: {
  },
  plugins: [createPersistedState({  // 使用 vuex-persistedstate 持久化状态
    key: 'my-app', // 本地存储的 key 名
    paths: ['username', 'identity','id'] // 只持久化 username 和 identity
  })]
});
