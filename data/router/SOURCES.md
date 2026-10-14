# 资料来源与适用范围

本次新增选择为 TP-Link Archer AX10 / Archer AX20，US，硬件 V1。没有将美国地区、V1 等同于所有地区或所有硬件版本。

knowledge.json 是对官方章节的简短中文整理，不是完整手册，也不是厂商原文逐字译本。每段包含可核对的官方 URL、章节、复核日期及稳定 evidence_id。网页可能随固件更新，实际界面不一致时应核对固件版本。

| 设备 | 官方版本入口 | 在线手册 |
|---|---|---|
| Archer AX10 US V1 | https://www.tp-link.com/us/support/download/archer-ax10/v1/ | https://www.tp-link.com/us/user-guides/archer-ax10%26ax1500_v1/ |
| Archer AX20 US V1 | https://www.tp-link.com/us/support/download/archer-ax20/v1/ | https://www.tp-link.com/us/user-guides/archer-ax20%26ax1800_v1/ |

已核对的章节：Appearance、Quick Setup、Manually Set Up Internet Connection、Access Point、Guest Network、Specify Wireless Settings、Firmware Upgrade、Backup & Restore，以及手册 FAQ Q3/Q4。AX20 的网络设置、设备管理分别为第 13/14 章；AX10 为第 12/13 章。

无线断连采用官方 FAQ 722（页面标注更新日期 2026-04-17）：https://www.tp-link.com/us/support/faq/722/。页面适用型号列出 AX10/AX20；本整理只纳入一般排查与前置条件，不声称每个固件均支持所有开关，也不迁移到未收录硬件版本。现象不完整时必须先确认有线连接和设备范围。

2026-10-14 在线初验后的资料修订：补全恢复区域中两个 RESTORE 的用途、保留登录信息的恢复对其他配置的处理、等待重启与备份注意事项；补全 FAQ 722 的前置条件及关闭 Smart Connect 的菜单。信道与带宽字段采用本型号 US V1 手册的 Specify Wireless Settings 章节。

固件适用范围另存为官方 FAQ 2796 摘要：https://www.tp-link.com/us/support/faq/2796/（页面标注更新日期 2026-04-23，适用型号列表含 AX10/AX20）。硬件版本、购买地区、有线升级与断电注意事项引用此来源；本型号手册中的升级菜单和操作仍保持各自章节引用。

普通重启保留设置的概念说明采用厂商通用文章：https://www.tp-link.com/ph/blog/1886/how-to-factory-reset-a-tp-link-router-when-to-do-it-and-how/（更新日期 2026-07-28）。这是菲律宾站上的通用概念文章，只采用“普通重启保留设置”的概念，不采用其他地区的等待时长、按钮、菜单、固件或恢复条件。它不扩展查询支持的地区，设备操作仍受 US V1 范围约束；部分恢复与完全恢复的区别仍以对应 US V1 手册为准。

系统提出补充固件版本、故障现象的追问是应用策略，不能伪装成上述官方章节中的要求。检索证据未覆盖某项内容时，只能说明本次证据不足，不能推断整个知识库或完整官方手册均未收录。

PDF/TXT 读取链仍可通过显式 RAG_PROFILE=demo 使用；生产 /retrieve 仅接受 router profile。旧演示资料不会进入路由器检索候选。

型号字段故意严格约束。本版本未收录 AX10 V2/V1.20、EU/CN，查询这些组合返回 unsupported_product，不借用 V1 US 操作。
