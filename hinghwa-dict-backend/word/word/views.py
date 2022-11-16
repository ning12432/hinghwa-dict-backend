import csv
import os

import demjson
import xlrd
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from article.models import Article
from website.views import (
    evaluate,
    token_check,
    simpleUserInfo,
    filterInOrder,
)
from ..forms import WordForm
from ..models import Word, User
from .word2pronunciation import word2pronunciation
from .dto.word_all import word_all
from .dto.word_simple import word_simple


@csrf_exempt
def searchWords(request):
    try:
        # WD0201 获取符合条件的字词的列表
        if request.method == "GET":
            words = Word.objects.filter(visibility=True)
            if "contributor" in request.GET:
                words = words.filter(contributor=request.GET["contributor"])
            if "search" in request.GET:
                result = []
                key = request.GET["search"].replace(" ", "")
                if not key[0].encode("utf-8").isalnum():
                    weights = [4, 2, 3, 1, 0.5, 0.5]
                    alpha = 1
                else:
                    weights = [2, 1, 1.5, 0.5, 3, 3]
                    alpha = 1
                for word in words:
                    if word.id == 4694 or word.id == 97:
                        t = 1
                    score = evaluate(
                        list(
                            zip(
                                [
                                    word.word,
                                    word.definition,
                                    word.mandarin,
                                    word.annotation,
                                    word.standard_pinyin,
                                    word.standard_ipa,
                                ],
                                weights,
                            )
                        ),
                        key,
                        alpha=alpha,
                    )
                    if score > 0:
                        result.append((word, score))
                result.sort(key=lambda a: a[1], reverse=True)
                if len(result) > 200:
                    result = result[:200]
                if len(result):
                    words = list(zip(*result))[0]
                else:
                    words = []
            result = [word_all(word) for word in words]
            words = [word.id for word in words]
            return JsonResponse({"result": result, "words": words}, status=200)
        # WD0102 管理员上传新词语
        elif request.method == "POST":
            body = demjson.decode(request.body)
            token = request.headers["token"]
            user = token_check(token, settings.JWT_KEY, -1)
            if user:
                body = body["word"]
                word_form = WordForm(body)
                if word_form.is_valid() and isinstance(body["mandarin"], list):
                    for id in body["related_articles"]:
                        Article.objects.get(id=id)
                    for id in body["related_words"]:
                        Word.objects.get(id=id)
                    word = word_form.save(commit=False)
                    word.contributor = user
                    word.visibility = True
                    word.save()
                    for id in body["related_articles"]:
                        article = Article.objects.get(id=id)
                        word.related_articles.add(article)
                    for id in body["related_words"]:
                        wordx = Word.objects.get(id=id)
                        word.related_words.add(wordx)
                    return JsonResponse({"id": word.id}, status=200)
                else:
                    return JsonResponse({}, status=400)
            else:
                return JsonResponse({}, status=401)
        # WD0202 词语内容批量获取
        elif request.method == "PUT":
            body = demjson.decode(request.body)
            words = []
            result = Word.objects.filter(id__in=body["words"])
            result = filterInOrder(result, body["words"])
            for word in result:
                pronunciation = word2pronunciation(word, "null")
                words.append(
                    {
                        "word": word_simple(word),
                        "contributor": simpleUserInfo(word.contributor),
                        "pronunciation": {"url": pronunciation, "tts": "null"},
                    }
                )
            return JsonResponse({"words": words}, status=200)
        else:
            return JsonResponse({}, status=405)
    except Exception as e:
        return JsonResponse({"msg": str(e)}, status=500)


@csrf_exempt
def manageWord(request, id):
    try:
        word = Word.objects.filter(id=id)
        if word.exists():
            word = word[0]
            # WD0101 获取字词的内容
            if request.method == "GET":
                word.views = word.views + 1
                word.save()
                return JsonResponse(
                    {"word": word_all(word)},
                    status=200,
                )
            # WD0103 管理员更改字词的内容
            elif request.method == "PUT":
                body = demjson.decode(request.body)
                token = request.headers["token"]
                if token_check(token, settings.JWT_KEY, word.contributor.id):
                    body = body["word"]
                    word_form = WordForm(body)
                    for key in body:
                        if (key in word_form) and len(word_form[key].errors.data):
                            return JsonResponse({}, status=400)
                    for key in body:
                        if key != "related_words" and key != "related_articles":
                            setattr(word, key, body[key])
                        elif key == "related_words":
                            for id in body["related_words"]:
                                Word.objects.get(id=id)
                            word.related_words.clear()
                            for id in body["related_words"]:
                                wordx = Word.objects.get(id=id)
                                word.related_words.add(wordx)
                        elif key == "related_articles":
                            for id in body["related_articles"]:
                                Article.objects.get(id=id)
                            word.related_articles.clear()
                            for id in body["related_articles"]:
                                article = Article.objects.get(id=id)
                                word.related_articles.add(article)
                    word.save()
                    return JsonResponse({}, status=200)
                else:
                    return JsonResponse({}, status=401)
            # WD0104 删除词语
            elif request.method == "DELETE":
                token = request.headers["token"]
                if token_check(token, settings.JWT_KEY, word.contributor.id):
                    word.delete()
                    return JsonResponse({}, status=200)
                else:
                    return JsonResponse({}, status=401)
            else:
                return JsonResponse({}, status=405)
        else:
            return JsonResponse({}, status=404)
    except Exception as e:
        return JsonResponse({"msg": str(e)}, status=500)


@require_POST
@csrf_exempt
def load_word(request):
    try:
        # WD0301 文件批量添加
        body = demjson.decode(request.body)
        file = body["file"]
        sheet = open(os.path.join("material", "word", file))
        lines = sheet.readlines()
        title = ["word", "definition"]
        col = 2
        for line in lines:
            info = line.split(",", 1)
            dic = {}
            for i in range(col):
                dic[title[i]] = info[i] if info[i] else "【待更新】"
            word_form = WordForm(dic)
            if word_form.is_valid():
                word = word_form.save(commit=False)
                word.contributor = User.objects.get(username="root")
                word.save()
                if word.id % 100 == 0:
                    print("load character {}".format(word.id))
            else:
                raise Exception("add fail in {}".format(dic))
        return JsonResponse({}, status=200)
    except Exception as e:
        return JsonResponse({"msg": str(e)}, status=500)


@csrf_exempt
def record(request):
    # PN0301 批量录音列表
    if request.method == "GET":
        words = Word.objects.filter(
            Q(standard_ipa__isnull=False)
            & Q(standard_pinyin__isnull=False)
            & Q(visibility=True)
        )
        pageSize = int(request.GET["pageSize"]) if "pageSize" in request.GET else 15
        page = int(request.GET["page"]) if "page" in request.GET else 1
        r = min(len(words), page * pageSize)
        l = min(len(words) + 1, (page - 1) * pageSize)
        result = [
            {
                "word": word.id,
                "ipa": word.standard_ipa,
                "pinyin": word.standard_pinyin,
                "count": word.pronunciation.count(),
                "item": word.word,
                "definition": word.definition,
            }
            for word in words[l:r]
        ]

        return JsonResponse(
            {
                "records": result,
                "total": {"item": len(words), "page": (len(words) - 1) // pageSize + 1},
            },
            status=200,
        )
    else:
        return JsonResponse({}, status=405)


@csrf_exempt
def upload_standard(request):
    """
    通过excel上传word的standard_pinyin，standard_ipa，分为三列，为别为id,pinyin,ipa，有表头
    :return: 返回名为conflict的csv，展示与数据库冲突的word字段，为5列，id,init_ipa,init_pinyin,ipa,pinyin
    """
    try:
        # WD0302 上传标准拼音和ipa
        if request.method == "POST":
            token = request.headers["token"]
            user = token_check(token, settings.JWT_KEY, -1)
            if user:
                file = request.FILES.get("file")

                sheet = xlrd.open_workbook(file_contents=file.read()).sheet_by_index(
                    0
                )  # 错误
                line = sheet.nrows
                col = sheet.ncols
                ids = [int(x.value) for x in sheet.col(0)[1:]]
                words = sorted(
                    list(Word.objects.filter(id__in=ids)), key=lambda w: w.id
                )

                # 将输入excel的词条按id从小到大排序
                infos = []
                for i in range(1, line):
                    info = sheet.row(i)
                    infos.append([int(info[0].value), info[1:]])
                infos.sort(key=lambda a: a[0])

                def conflict(x, y):
                    return x and y and x != y

                conflicts = []
                j = 0
                for i in range(line):
                    while j < len(words) and words[j].id < infos[i][0]:
                        j += 1
                    if j < len(words) and words[j].id == infos[i][0]:
                        if conflict(
                            words[j].standard_ipa, infos[i][1][1].value
                        ) or conflict(words[j].standard_pinyin, infos[i][1][0].value):
                            conflicts.append(
                                [
                                    words[j].id,
                                    words[j].standard_ipa,
                                    words[j].standard_pinyin,
                                    infos[i][1][1].value,
                                    infos[i][1][0].value,
                                ]
                            )
                        words[j].standard_ipa = infos[i][1][1].value
                        words[j].standard_pinyin = infos[i][1][0].value
                        words[j].save()
                        j += 1
                        if j % 100 == 0:
                            print(j)

                response = HttpResponse(
                    content_type="text/csv", status=200, encoding="ANSI"
                )
                response["Content-Disposition"] = "attachment; filename=conflict.csv"
                title = ["单词ID", "原IPA", "原拼音", "现IPA", "现拼音"]
                file = csv.writer(response)
                file.writerow(title)
                file.writerows(conflicts)
                return response
            else:
                return JsonResponse({}, status=401)
        else:
            return JsonResponse({}, status=405)
    except Exception as e:
        return JsonResponse({"msg": str(e)}, status=500)