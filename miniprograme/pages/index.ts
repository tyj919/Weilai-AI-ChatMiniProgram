Page({
    data: {
      msg: "",
      chatList: [
        {
          type: 0,
          content: "你好呀！欢迎来到蔚来的大家庭~购车之前有什么疑问呢？是不是对蔚来哪款车感兴趣呀？比如智能电动全能SUV ES6、溜背造型的EC6，还是SUV ES8"
        }
      ]
    },
    getInput(e: any) {
      this.setData({
        msg: e.detail.value
      })
    },
    async sendMsg() {
      const text = this.data.msg.trim()
      if (!text) return
      // 用户消息入列表
      let arr = [...this.data.chatList]
      arr.push({ type: 1, content: text })
      this.setData({ chatList: arr, msg: "" })
      // 替换成你cpolar/云服务器接口地址
      const url = "https://xxx.cpolar.top/chat"
      wx.request({
        url,
        method: "POST",
        data: { question: text },
        success: res => {
          arr.push({ type: 0, content: res.data.ans })
          this.setData({ chatList: arr })
        }
      })
    }
  })