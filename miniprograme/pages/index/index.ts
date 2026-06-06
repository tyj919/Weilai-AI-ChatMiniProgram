interface ChatItem {
  type: 0 | 1
  content: string
}

interface ChatResponse {
  ans?: string
  answer?: string
}

Page({
  data: {
    msg: "",
    scrollTo: "",
    chatList: [
      {
        type: 0,
        content:
          "你好呀！欢迎来到蔚来的大家庭~购车之前有什么疑问呢？是不是对蔚来哪款车感兴趣呀？比如智能电动全能SUV ES6、溜背造型的EC6，还是SUV ES8"
      }
    ] as ChatItem[]
  },

  getInput(e: WechatMiniprogram.Input) {
    this.setData({
      msg: e.detail.value
    })
  },

  sendMsg() {
    const text = this.data.msg.trim()
    if (!text) return

    const chatList = [...this.data.chatList, { type: 1 as const, content: text }]
    this.setData({
      chatList,
      msg: "",
      scrollTo: `msg-${chatList.length - 1}`
    })

    // 开发：微信开发者工具勾选「不校验合法域名」后可用局域网 IP
    // 上线：改为 cpolar / 云服务器 HTTPS 地址
    const url = "http://127.0.0.1:5000/chat"
    wx.request({
      url,
      method: "POST",
      header: { "content-type": "application/json" },
      data: { question: text },
      success: (res) => {
        const data = res.data as ChatResponse
        const reply =
          (data?.ans || data?.answer)?.trim() || "抱歉，暂时无法回答您的问题"
        const list = [...this.data.chatList, { type: 0 as const, content: reply }]
        this.setData({
          chatList: list,
          scrollTo: `msg-${list.length - 1}`
        })
      },
      fail: () => {
        const list = [
          ...this.data.chatList,
          { type: 0 as const, content: "网络异常，请稍后再试" }
        ]
        this.setData({
          chatList: list,
          scrollTo: `msg-${list.length - 1}`
        })
      }
    })
  }
})
