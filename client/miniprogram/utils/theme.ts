// 主题管理工具
export interface ThemeColors {
  pageBackground: string
  containerBackground: string
  primaryText: string
  secondaryText: string
  tertiaryText: string
  errorText: string
  border: string
  primaryButton: string
  primaryButtonText: string
  accentText: string
  todayBackground: string
  todayText: string
}

const darkTheme: ThemeColors = {
  pageBackground: '#1B1B1B',
  containerBackground: '#131314',
  primaryText: '#C9D1D9',
  secondaryText: '#C4C7C5',
  tertiaryText: '#8B949E',
  errorText: '#F85149',
  border: 'rgba(255,255,255,0.08)',
  primaryButton: '#A8C7FA',
  primaryButtonText: '#062E6F',
  accentText: '#A8C7FA',
  todayBackground: '#A8C7FA',
  todayText: '#131314'
}

const lightTheme: ThemeColors = {
  pageBackground: '#FFFFFF',
  containerBackground: '#F8F9FA',
  primaryText: '#202124',
  secondaryText: '#5F6368',
  tertiaryText: '#9AA0A6',
  errorText: '#D93025',
  border: 'rgba(0,0,0,0.08)',
  primaryButton: '#1A73E8',
  primaryButtonText: '#FFFFFF',
  accentText: '#1A73E8',
  todayBackground: '#1A73E8',
  todayText: '#FFFFFF'
}

export function getCurrentTheme(): ThemeColors {
  const app = getApp<IAppOption>()
  const isDark = app?.globalData?.darkMode !== false
  return isDark ? darkTheme : lightTheme
}

export function applyThemeToPage(page: any) {
  const theme = getCurrentTheme()
  page.setData({
    themeColors: theme
  })
}