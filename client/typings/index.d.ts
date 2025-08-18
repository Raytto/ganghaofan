/// <reference path="./types/index.d.ts" />

interface IAppOption {
  globalData: {
    userInfo?: WechatMiniprogram.UserInfo,
    debugMode?: boolean,
    isAdmin?: boolean,
    adminViewEnabled?: boolean,
    darkMode?: boolean,
  }
  userInfoReadyCallback?: WechatMiniprogram.GetUserInfoSuccessCallback,
  switchTheme?: (darkMode: boolean) => void,
}