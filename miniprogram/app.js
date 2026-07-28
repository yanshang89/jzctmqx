// app.js - 小程序全局逻辑
App({
  // 全局共享数据
  globalData: {
    // 后端服务器地址，部署时改成你自己的 HTTPS 域名
    // 本地开发可使用 http://127.0.0.1:5000，真机调试需用 https
    baseUrl: 'http://127.0.0.107:5000',
    // 授权状态
    authPassed: false,
    // 用户配置
    config: null
  },

  onLaunch() {
    // 小程序启动时执行
    console.log('小飞拓客小程序启动');

    // 从本地缓存读取配置
    const cfg = wx.getStorageSync('user_config');
    if (cfg) {
      this.globalData.config = cfg;
    }
  }
});
