from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.base import View
from search.models import ArticleType, LagouType, ChemicalBookType
from elasticsearch import Elasticsearch
import time
import redis

client = Elasticsearch(hosts=['127.0.0.1'])
redis_cli = redis.StrictRedis()


class SearchSuggest(View):
    def get(self, request):
        输入字 = request.GET.get('s', '')
        搜索类型 = request.GET.get('s_type', 'article')
        搜索建议标题 = []
        if 输入字:
            if 搜索类型 == 'article':
                s = ArticleType.search().suggest('my_suggest', 输入字, completion={
                    'field': '建议', 'fuzzy': {'fuzziness': 2}, 'size': 10
                })
            elif 搜索类型 == 'job':
                s = LagouType.search().suggest('my_suggest', 输入字,completion={
                    'field': '建议','fuzzy': {'fuzziness': 2},'size': 10
                })
            suggestions = s.execute_suggest()
            for math in suggestions.my_suggest[0].options:
                source = math._source
                搜索建议标题.append(source['标题'])

        return JsonResponse(搜索建议标题, safe=False)


class SearchView(View):
    def get(self, request):
        搜索词 = request.GET.get('q', '')
        搜索类型 = request.GET.get('s_type', 'article')
        redis_cli.zincrby('热门搜索词', 1, 搜索词)
        热门搜索词列表 = redis_cli.zrevrangebyscore('热门搜索词', '+inf', '-inf', start=0, num=5)
        热门搜索词列表 = map(lambda x:x.decode('utf-8'), 热门搜索词列表)
        页数 = int(request.GET.get('p', '1'))
        开搜索时间 = time.time()
        if 搜索类型 == 'article':
            搜索返回结果 = client.search(
                index='jobbole',
                body={
                    'query': {
                        'multi_match': {
                            'query': 搜索词,
                            'fields': ['标题', '类型列表', '文章内容']
                        }
                    },
                    'from': (页数-1)*10,
                    'size': 10,
                    'highlight': {
                        'pre_tags': ['<span class="keyWord">'],
                        'post_tags': ['</span>'],
                        'fields': {
                            '标题': {},
                            '文章内容': {}
                        }
                    }
                }
            )
            jobole数量 = redis_cli.get('jobole数量')
        elif 搜索类型 == 'job':
            搜索返回结果 = client.search(
                index='job',
                body={
                    'query': {
                        'multi_match': {
                            'query': 搜索词,
                            'fields': ['招聘职位名称', '工作标签', '职位描述']
                        }
                    },
                    'from': (页数-1)*10,
                    'size': 10,
                    'highlight': {
                        'pre_tags': ['<span class="keyWord">'],
                        'post_tags': ['</span>'],
                        'fields': {
                            '招聘职位名称': {},
                            '职位描述': {}
                        }
                    }
                }
            )
            工作数量 = redis_cli.get('工作数量')
        elif 搜索类型 == 'chemicalbook':
            搜索返回结果 = client.search(
                index='chemicalbook',
                body={
                    'query': {
                        'multi_match': {
                            'query': 搜索词,
                            'fields': ['中文名称', '英文名称', '化学式']
                        }
                    },
                    'from': (页数-1)*10,
                    'size': 10,
                    'highlight': {
                        'pre_tags': ['<span class="keyWord">'],
                        'post_tags': ['</span>'],
                        'fields': {
                            '中文名称': {},
                            '英文名称': {}
                        }
                    }
                }
            )
            化学品数量 = redis_cli.get('化学品数量')

        结束搜索时间 = time.time()
        搜索耗时 = 结束搜索时间 - 开搜索时间

        结果数量 = 搜索返回结果['hits']['total']
        总页数 = int(结果数量/10)+1
        结果列表 = []
        for 单个结果 in 搜索返回结果['hits']['hits']:
            单个结果字典 = {}
            if  搜索类型 == 'article':
                if '标题' in 单个结果['highlight']:
                    单个结果字典['标题'] = 单个结果['highlight']['标题'][0]
                else:
                    单个结果字典['标题'] = 单个结果['_source']['标题']
                if '文章内容' in 单个结果['highlight']:
                    单个结果字典['文章内容'] = 单个结果['highlight']['文章内容']
                else:
                    单个结果字典['文章内容'] = 单个结果['_source']['文章内容']
                单个结果字典['创建日期'] = 单个结果['_source']['创建日期']
                单个结果字典['文章url'] = 单个结果['_source']['文章url']
                单个结果字典['得分'] = 单个结果['_score']
                单个结果字典['搜索类型'] = '伯乐在线'
            elif 搜索类型 == 'job':
                if '中文名称' in 单个结果['highlight']:
                    单个结果字典['中文名称'] = 单个结果['highlight']['中文名称'][0]
                else:
                    单个结果字典['中文名称'] = 单个结果['_source']['中文名称']
                if '英文名称' in 单个结果['highlight']:
                    单个结果字典['英文名称'] = 单个结果['highlight']['英文名称']
                else:
                    单个结果字典['英文名称'] = 单个结果['_source']['英文名称']
                单个结果字典['化学式'] = 单个结果['_source']['化学式']
                单个结果字典['化学结构式图片url'] = 单个结果['_source']['化学结构式图片url']
                单个结果字典['得分'] = 单个结果['_score']
                单个结果字典['搜索类型'] = '拉勾网'
            elif 搜索类型 == 'chemicalbook':
                if '中文名称' in 单个结果['highlight']:
                    单个结果字典['中文名称'] = 单个结果['highlight']['中文名称'][0]
                else:
                    单个结果字典['中文名称'] = 单个结果['_source']['中文名称']
                if '英文名称' in 单个结果['highlight']:
                    单个结果字典['英文名称'] = 单个结果['highlight']['英文名称']
                else:
                    单个结果字典['英文名称'] = 单个结果['_source']['英文名称']
                单个结果字典['化学结构式图片url'] = 单个结果['_source']['化学结构式图片url']
                单个结果字典['得分'] = 单个结果['_score']
                单个结果字典['搜索类型'] = '化学品'

            结果列表.append(单个结果字典)

        return  render(request, 'result.html', {'结果列表': 结果列表, '搜索词': 搜索词, '页数': 页数, '结果数量': 结果数量, '总页数': 总页数, '搜索耗时': 搜索耗时, 'jobole数量': jobole数量 , '工作数量': 工作数量, '化学品数量':化学品数量, '热门搜索词列表':热门搜索词列表})
