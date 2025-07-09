# LinkedIn 关键词分析系统

## 项目概述

本项目是一个综合性的LinkedIn职位关键词分析系统，通过爬取LinkedIn上特定地区和关键词的职位描述，结合传统NLP和Gemini-2.0-Flash-Exp大语言模型，提取和分析职位所需的关键技能，并通过可视化展示结果。

## 功能特点

- **智能爬虫**：使用Selenium配合多种反爬技术，稳定抓取LinkedIn职位数据
- **LLM分析**：调用Gemini-2.0-Flash-Exp对职位描述进行摘要和技能抽取
- **混合分析**：融合传统词频统计与LLM抽取结果，提供更全面的关键词分析
- **丰富可视化**：生成热力图、词云等多种可视化图表
- **交互界面**：通过Gradio提供友好的用户交互体验

## 项目结构

```
linkedin_keywords/
├── requirements.txt          # 项目依赖
├── README.md                 # 项目说明文档
├── config.py                 # 配置文件
├── main.py                   # 主程序入口
├── app.py                    # Gradio应用程序
├── data/                     # 数据存储目录
│   ├── raw/                  # 原始爬取数据
│   └── processed/            # 处理后的数据
├── logs/                     # 日志文件
├── output/                   # 输出结果
│   ├── excel/                # Excel结果文件
│   └── visualizations/       # 可视化图表
├── src/                      # 源代码
│   ├── crawler/              # 爬虫模块
│   │   ├── __init__.py
│   │   ├── linkedin_crawler.py  # LinkedIn爬虫
│   │   └── anti_detect.py    # 反检测模块
│   ├── processor/            # 数据处理模块
│   │   ├── __init__.py
│   │   ├── excel_handler.py  # Excel处理
│   │   └── text_cleaner.py   # 文本清洗
│   ├── analyzer/             # 分析模块
│   │   ├── __init__.py
│   │   ├── llm_extractor.py  # LLM技能抽取
│   │   ├── freq_analyzer.py  # 词频分析
│   │   └── hybrid_analyzer.py # 混合分析
│   └── visualizer/           # 可视化模块
│       ├── __init__.py
│       ├── heatmap.py        # 热力图生成
│       └── wordcloud.py      # 词云生成
└── tests/                    # 测试代码
    ├── test_crawler.py
    ├── test_processor.py
    └── test_analyzer.py
```

## 安装步骤

1. 克隆或下载本项目代码

2. 安装所需依赖包：

```bash
pip install -r requirements.txt
```

3. 安装Chrome浏览器和ChromeDriver（确保版本匹配）

4. 获取Google Gemini API密钥：
   - 访问[Google AI Studio](https://makersuite.google.com/app/apikey)
   - 创建API密钥
   - 在`config.py`中配置您的API密钥

## 使用方法

### 1. 配置参数

编辑`config.py`文件，设置：
- LinkedIn账号信息（可选）
- 目标搜索关键词和地区
- 爬取页数和频率控制
- API密钥和模型参数

### 2. 运行爬虫

```bash
python -m src.crawler.linkedin_crawler
```

### 3. 分析数据

```bash
python -m src.analyzer.hybrid_analyzer
```

### 4. 启动Gradio界面

```bash
python app.py
```

在浏览器中访问显示的本地地址（通常是http://127.0.0.1:7860）

## 注意事项

- 请遵守LinkedIn的使用条款和robots.txt规定
- 控制爬取频率，避免IP被封
- 首次使用时建议手动登录LinkedIn并保存Cookie
- 大型数据集处理可能需要较长时间
- Gemini API有使用限制和费用，请合理使用

## 许可证

本项目使用MIT许可证。