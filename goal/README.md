# Goal_planning

将paddlepaddle代码迁移到pytorch上，对baseline做了大量bug修正，添加大量注释，优化文件结构

## 文件结构

- data
  - origin：原始数据
  - process：中间处理数据
  - train：训练和测试用数据
  - others：word dict, stop words，type dict, type 邻居们，entity dict, entity 邻居们以及baseline提供的额外entity关系
  - 由于process和train过大，没有传上去
- model
  - goal_finish：预测当前goal（这一轮对话）是否完成
  - next_goal_type：给出bot回复内容的type
  - next_goal_entity：给出bot回复内容的entity
  - goal_planning：生成测试集中的type entity
- output
  - 训练好的模型和测试集生成结果
- utils
  - data_process：数据预处理 origin -> process
  - data_generator：给出type entity dict和邻居图，再处理训练用数据，生成测试用数据 process -> train, others
  - train_generator：生成训练用数据 process -> train

> 测试集中需要补全的都是bot回复的内容

补全目标转移序列，有如下几个子任务：
1. 预测当前goal（这一轮对话）是否完成
2. 给出bot回复内容的type
3. 给出bot回复内容的entity

## 训练

### 预测当前goal（这一轮对话）是否完成

- X
  - bot回复的前一句，即用户说的最后一句
  - bot回复的前一句的type
- y
  - 是否完成，可以通过是否为一轮对话的开头判断
    - 注意，一个session的第一句虽然也是一轮对话的开头，但是明显没有完成
- 模型
  - 句子跑一个LSTM
  - type对LSTM的hidden做attention
    - 比baseline提升6个点，到91
  - 最后做全连接

### 给出bot回复内容的type

统计train, val中出现的相邻type，作为解空间

- X
  - 历史 goal type seq+ 前一个 goal type 的邻居
  - 前一个 goal type 的邻居
  - 倒数第二个 goal type
- y
  - 邻居是不是真正的type
- 模型
  - goal type seq跑一个LSTM
  - 实验发现有没有goal type 的邻居 和 倒数第二个 goal type几乎没有影响
- 问题
  - 验证集准确率81，但实际测试时问题不大，因为解空间被大大缩小
  - 寒暄后面的type效果不好，因为寒暄可以接不少类型，而且寒暄本身对后面没有什么提示作用
  - 这样看，倒数第二个type应该有些用处，但实际几乎没效果

### 给出bot回复内容的entity

统计train, val中出现的相邻entity，加上baseline中给出的补充关系，作为解空间

- X
  - 历史 goal entity seq+ 前一个 goal entity 的邻居
  - 前一个 goal entity 的邻居
  - 最后一个 goal entity
- y
  - 邻居是不是真正的 entity
- 模型
  - goal type seq跑一个LSTM
  - 实验发现有没有goal type 的邻居 和 倒数第二个 goal type几乎没有影响
- 问题
  - 验证集准确率85
  - 预测效果不好，因为解空间大于5的entity有将近100个

## 测试

### 流程

1. 找出当前对话是第几轮
2. 如果是第一轮或者倒数第三轮，预测是否完成，完成加一轮
3. 如果更新后是第一轮或者倒数两轮，直接用数据中给出的标答
4. 如果处在中间缺失的位置，用模型预测type entity

### 问题

- entity的预测质量低，原因：
  - entity总数1363，解空间大于5的entity有将近100个，相比之下type总数只有21
  - 输入特征少：由于只给出了第一个和最后两个，预测时只能用上第一个和它的邻居（候选解）
- type entity 怎么在生成对话中用起来
- user profile, kg怎么用起来

### 想法
- 向entity模型中加入bot回复的前一句，即用户说的最后一句
- 预测时去掉在user profile和kg中没有出现过的entity