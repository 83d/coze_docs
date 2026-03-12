原文地址：https://docs.coze.cn/developer_guides

# API 介绍

[扣子编程](https://code.coze.cn/home)是新一代一站式 AI 智能体开发平台。无论你是否有编程基础，都可以在平台上快速搭建基于 AI 模型的各类问答智能体。而且你可以将搭建的智能体发布到各类社交平台和通讯软件上，让更多的用户与你搭建的智能体聊天。

[扣子编程](https://code.coze.cn/home)支持将 AI 智能体和扣子应用发布为 API 服务，你可以通过 HTTP 方式与其进行交互。

## 费用说明

- **个人免费版**：免费使用[扣子编程](https://code.coze.cn/home) API，但有一定的额度限制。

- **个人付费版（进阶版、高阶版、旗舰版）、企业版（企业标准版、企业旗舰版）**：涉及大模型处理的 API 会产生模型费用，音视频的 API 也有对应功能的计费方式。

## 限制说明

### 限流策略

[扣子编程](https://code.coze.cn/home) API 限流策略分为以下两个维度，且不同用户类型的限流策略不同。

| **限流策略** | **个人免费版** | **个人付费版** | **企业标准版** | **企业旗舰版** |
| --- | --- | --- | --- | --- |
| [发起对话](https://docs.coze.cn/developer_guides/chat_v3) API 的流控 | 20 QPS | 100 QPS | 200 QPS | 500 QPS |
| 以下关键 API 的流控：  - [执行工作流](https://docs.coze.cn/developer_guides/workflow_run)  - [执行工作流（流式响应）](https://docs.coze.cn/developer_guides/workflow_stream_run)  - [执行对话流](https://docs.coze.cn/developer_guides/workflow_chat)  - [查询工作流异步运行结果](https://docs.coze.cn/developer_guides/workflow_history)  - [查询输出节点的执行结果](https://docs.coze.cn/developer_guides/get_node_execute_history_response)  | 50 QPS | 100 QPS | 200 QPS | 500 QPS  企业超级管理员或管理员可以扩容 API 的 QPS，具体步骤请参见[购买扩容服务](https://docs.coze.cn/coze_pro/resource_expansion_fee)。 |
| [上传文件](https://docs.coze.cn/developer_guides/upload_files)API 的流控 | 10 QPS | 10 QPS | 20 QPS | 20 QPS |
| 模型流控。  调用[发起对话](https://docs.coze.cn/developer_guides/chat_v3)、[执行工作流](https://docs.coze.cn/developer_guides/workflow_run)、[执行工作流（流式响应）](https://docs.coze.cn/developer_guides/workflow_stream_run)、[执行对话流](https://docs.coze.cn/developer_guides/workflow_chat)等涉及模型处理的 API 时，每个用户使用模型的流控。 | 模型每分钟请求数（RPM）为 300。 | 模型每分钟请求数（RPM）为 1000。 | 模型每分钟请求数（RPM）为 5000。     | 模型每分钟请求数（RPM）为 12000。 |
| API调用量 | 累计 500 次免费额度。  [!NOTE]  **说明**  一旦累计调用次数超过免费额度，此账号将无法继续使用任何[扣子编程](https://code.coze.cn/home) API。API 免费额度不适用于通过[扣子编程](https://code.coze.cn/home)、其他发布渠道或 SDK 产生的请求。  | 不限 | 不限 | 不限 |

### 请求体限制

API 请求体大小限制如下：

- 工作流相关的 API 请求体大小限制为 20MB。

- 其他类类别的 API 请求体大小限制为 15MB。

## 发送请求

将以下命令粘贴到终端中以运行你的第一个 API 请求。

在发送请求前，请将示例中的以下参数值替换成真实数据：

- Authorization：生成的个人访问令牌。线上环境注意替换为 OAuth 访问密钥，详情参考[OAuth 应用管理](https://docs.coze.cn/developer_guides/oauth_apps)。

- bot\_id：智能体ID。进入智能体的开发页面，开发页面 URL 中 bot 参数后的数字就是智能体ID。例如https://www.coze.cn/space/341\*\*\*\*/bot/73428668\*\*\*\*\*，bot\_id 为73428668\*\*\*\*\*。

- > [!NOTE]
  >
  > **说明**
  >
  > 确保智能体已发布为 API 服务。详情参考[准备工作](https://docs.coze.cn/developer_guides/preparation)。


- user\_id：标识当前与智能体交互的用户。调试时可将此参数固定为一个任意字符串，例如 123。

- content：发送的消息内容。

-

  curl --location --request POST 'https://api.coze.cn/v3/chat' \

  --header 'Authorization: Bearer pat\_OYDacMzM3WyOWV3Dtj2bHRMymzxP\*\*\*\*' \

  --header 'Content-Type: application/json' \

  --data-raw '{

  "bot\_id": "73428668\*\*\*\*\*",

  "user\_id": "123123\*\*\*",

  "stream": false,

  "auto\_save\_history":true,

  "additional\_messages":[

  {

  "role":"user",

  "content":"早上好",

  "content\_type":"text"

  }

  ]

  }'


- > [!NOTE]
  >
  > **说明**
  >
  > 如果需要通过火山引擎私有网络访问扣子编程 API ，请参见[通过私网连接访问扣子 API](https://docs.coze.cn/dev_how_to_guides/access_api_over_vpc)。


## 基础概念

| **名词** | **说明** |
| --- | --- |
| 会话（Conversation） | 智能体和用户之间的一段问答交互。一个会话包含一条或多条消息，并且能够自动处理截断，以适应模型的上下文内容。 |
| 消息（Message） | 一条由用户或智能体创建的消息，消息内容可以包括文本、图片或文件。消息以列表的形式储存在对话中。 |
| 对话（Chat） | 在会话中对智能体的一次调用。智能体收到请求后，结合用户输入、通过预设的一系列工作流等配置来调用模型或工具执行指定任务。每个对话都是会话的一部分，智能体会将对话中产生的消息添加到会话中。  你可以直接发起对话，与智能体进行一次交互；也可以创建会话和消息，并在指定会话中发起对话，会话中的其他消息会作为历史消息传递给大模型。 |
| 上下文段落（Section） | 在智能体对话管理中，Section 是一个独立的上下文段落，用于分隔不同的对话阶段或主题。创建会话时会生成一个 Section，Section 中包含上下文消息，当用户清除上下文时，系统会创建一个新的 Section，从而确保新的对话不受历史消息的影响。  会话、消息和上下文段落的关系如下图所示。   <img src="https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/e4b55816254c4446ae59bbca33ca8e1d~tplv-goo7wpa0wc-quality:q75.awebp" width="1052">  |

下一篇
