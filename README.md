<p align="right"><a href="./README.en.md">English</a> &nbsp;·&nbsp; 简体中文</p>

<img src="./docs/images/brand.svg" alt="司凤星球标记" width="72" height="72">

<sub>SIFENG RADIO &nbsp;/&nbsp; 001</sub>

# 司凤星球

### 只听喜欢的。

从哔哩哔哩找到与「司凤」「司凤版」「隆德齐」有关的声音。点开一首，音乐就开始；收藏、记录与播放控制留在手边，其余都安静退后。

**Windows 桌面版** &nbsp;·&nbsp; **Android 手机版** &nbsp;·&nbsp; **中文界面**

<br>

<img src="./docs/images/discover.png" alt="司凤星球桌面版发现页：白色界面、搜索框和视频列表" width="100%">

<sub>01 / 发现页 · 输入歌名或歌手，直接搜索新的结果，不局限于已加载列表。</sub>

---

## 听歌这件事，可以简单一点

**找得到。** 搜索词会分别与「司凤」「司凤版」「隆德齐」组合；结果标题仍需包含指定词。手机版的搜索结果按“高播放量 → 随机”交替呈现。

**点开就听。** 桌面版边传输边缓存，不必等待整首歌曲下载完成；手机版使用原生播放器。上一首、下一首、暂停、重播和随机播放都在熟悉的位置。

**离开界面，音乐还在。** 桌面窗口可以收进托盘；推荐卡收起后，仍能从「正在播放」找到歌曲。可选的悬浮胶囊会显示当前曲目。

## 从你的习惯开始

首次进入时，配置会一步一步展开；搜索词、播放方式、关闭行为和悬浮胶囊都能之后再改。

<p align="center">
  <img src="./docs/images/onboarding.png" alt="首次进入：司凤星球欢迎界面" width="49%">
  <img src="./docs/images/preferences.png" alt="桌面版偏好设置界面" width="49%">
</p>

<sub>02 / 左：首次进入 &nbsp;·&nbsp; 右：偏好设置</sub>

## 喜欢的，留下来

本地收藏与「司凤记录」保存你想再听的歌。悬浮胶囊只占一小块空间，封面缓慢旋转，播放状态一眼可见。

<img src="./docs/images/capsule.png" alt="显示封面与歌曲名称的悬浮播放胶囊" width="320">

<details>
<summary>查看本地收藏界面</summary>
<br>
<img src="./docs/images/favorites.png" alt="司凤星球本地收藏界面" width="100%">
</details>

---

## 下载

在仓库的 **Releases** 页面获取安装包。二进制文件适合放在 Releases，而不是直接提交到源码仓库。

| 平台 | 文件 | 打开方式 |
|:--|:--|:--|
| Windows | `SiFengPlanet.exe` | 双击运行，无额外命令行窗口。 |
| Android 8.0 及以上 | `sifeng_planet_android.apk` | 安装后打开；悬浮胶囊仅在启用时请求系统授权。 |

<details>
<summary>从源码运行与构建</summary>

Windows 版需要 Python、PySide6 与 requests：

```powershell
py -m pip install -r outputs/requirements.txt
py outputs/sifeng_planet.pyw
```

Android 版需要 Android SDK 34 与 Gradle：

```powershell
cd mobile
gradle :app:assembleDebug
```

桌面完整媒体缓存位于 `%LOCALAPPDATA%\SiFengPlanet\Cache`；偏好、收藏与历史位于 `%APPDATA%\SiFengPlanet`。手机端数据保存在本机应用数据中，两个平台的数据暂不互通。使用时需要联网。

</details>

## 许可与说明

本项目原创代码和自制界面素材采用 [PolyForm Noncommercial 1.0.0](./LICENSE)：可在该许可范围内进行**非商用**使用、修改与分发；这不是 MIT 许可证。

司凤星球是非官方个人项目，与哔哩哔哩无隶属关系。截图中的封面、视频标题，以及搜索到的视频与音乐均属于各自权利人，不包含在本项目的许可中。
