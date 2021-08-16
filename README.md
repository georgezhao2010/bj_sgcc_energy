# 北京用电信息查询

通过“国网北京电力”微信公众号的接口，采集你的家庭用电信息。

# 使用之前
首先关注“国网北京电力”微信公众号，打开微营业厅->个人中心->户号关联，确保你至少已关联至少一个北京国网电力的户号。如果没有关联，在此进行户号关联操作。此时点开微营业厅，应已经可以看到关联的用户，点击用户，可以看到该用户的用电信息。

使用任何网络抓包软件，如安卓手机的Fiddler， 苹果手机的Stream，进行抓包，过滤条件可以选择"HTTP"。抓包时在微营业厅上进行操作，查看一下用电信息。看到HTTP HEADER中有内容为“user_openid=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX”的内容，将user_openid=后的内容复制下来，如果最后是以\r\n结尾，则去掉\r\n，如果后部包含等于号"="，保留等于号。这个字符串就是openid，保存备用。

![screenshot](https://user-images.githubusercontent.com/27534713/129531245-c5190326-3258-4181-a8e9-e86598ff27bf.png)


# 安装
使用HACS以自定义存储库方式安装，或者从[Latest release](https://github.com/georgezhao2010/bj_sgcc_energy/releases/latest)下载最新的Release版本，将其中的`custom_components/bj_sgcc_engergy`放到你的Home Assistant的`custom_components/bj_sgcc_engergy`中。

# 配置
在configuration.yaml中，增加配置如下：
```
bj_sgcc_energy:
  openid: 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX' #此为微信公众号中抓取的openid
```
重新启动Home Assistant

# 特性
- 如果公众号中关联了多个北京国电用户，则支持多个用户用电信息的采集。
- 支持实时用电单价实体，可用于Home Assistant 2021.8.X最新的能源模块的实时电费计算。

该组件支持的组件如下
## 传感器
包含(19 * 关联用户数)个传感器
|  entity_id形式   | 含义  |
|  ----  | ----  |
| sensor.XXXXXXXXXX_balance | 电费余额 |
| sensor.XXXXXXXXXX_current_level | 当前用电阶梯 |
| sensor.XXXXXXXXXX_current_level_consume | 当前阶梯用电 |
| sensor.XXXXXXXXXX_current_level_remain | 当前阶梯剩余额度 |
| sensor.XXXXXXXXXX_current_price | 当前电价 |
| sensor.XXXXXXXXXX_year_consume | 本年度用电量 |
| sensor.XXXXXXXXXX_year_consume_bill | 本年度电费 |
| sensor.XXXXXXXXXX_history_* | 过去12个月用电情况 |

其中XXXXXXXXXX为北京国电用户户号， \*取值为1-12

# 示例
历史数据采用[flex-table-card](https://github.com/custom-cards/flex-table-card)展示，你也可以根据需要采用自己的展示形式
![screenshot](https://user-images.githubusercontent.com/27534713/129530748-0f3d980b-357f-4538-b4b4-4f4f65e3df48.png)


# 特别鸣谢
[瀚思彼岸论坛](https://bbs.hassbian.com/)的[@crazysiri](https://https://bbs.hassbian.com/thread-13355-1-1.html)，直接使用了他的部分代码。

