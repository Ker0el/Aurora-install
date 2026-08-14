# -*- coding: utf-8 -*-
"""核心逻辑单元测试（无 PyQt6 依赖，使用 sys.modules 注入 mock Qt 模块）"""
import os
import sys
import json
import shutil
import tempfile
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ---------------- mock PyQt6 / qfluentwidgets ----------------

def _make_fake_module(name, attrs=None):
    m = types.ModuleType(name)
    m.__dict__.update(attrs or {})
    sys.modules[name] = m
    return m


class _AnyCls:
    def __init__(self, *a, **k):
        pass


class _DynamicModule(types.ModuleType):
    """任意属性名返回一个可用作基类/可实例化的假类"""

    def __getattr__(self, name):
        return type(f"{self.__name__}.{name}", (_AnyCls,), {})


def _pyqt_signal(*a, **k):
    return object()


def _pyqt_slot(*a, **k):
    def deco(f):
        return f
    return deco


_Qt = types.SimpleNamespace()


class _QLocale(_AnyCls):
    Language = types.SimpleNamespace(
        Chinese='Chinese', English='English', French='French', Russian='Russian',
        German='German', Japanese='Japanese', Korean='Korean',
        TraditionalChinese='TraditionalChinese', Spanish='Spanish')
    Country = types.SimpleNamespace(
        China='China', UnitedStates='UnitedStates', France='France', Russia='Russia',
        Germany='Germany', Japan='Japan', Taiwan='Taiwan', HongKong='HongKong',
        SouthKorea='SouthKorea', Spain='Spain')


_make_fake_module('PyQt6', {})
_make_fake_module('PyQt6.QtCore', {
    'Qt': _Qt, 'pyqtSignal': _pyqt_signal, 'pyqtSlot': _pyqt_slot,
    'QThread': _AnyCls, 'QObject': _AnyCls, 'QTimer': _AnyCls,
    'QUrl': _AnyCls, 'QSize': _AnyCls, 'QLocale': _QLocale, 'QTranslator': _AnyCls,
})
_make_fake_module('PyQt6.QtWidgets', {
    'QApplication': _AnyCls, 'QWidget': _AnyCls, 'QVBoxLayout': _AnyCls,
    'QHBoxLayout': _AnyCls, 'QLabel': _AnyCls,
})
_make_fake_module('PyQt6.QtGui', {
    'QIntValidator': _AnyCls, 'QIcon': _AnyCls, 'QPixmap': _AnyCls,
    'QFont': _AnyCls, 'QDesktopServices': _AnyCls,
})
_make_fake_module('PyQt6.QtNetwork', {
    'QNetworkAccessManager': _AnyCls, 'QNetworkRequest': _AnyCls, 'QNetworkReply': _AnyCls,
})
sys.modules['qfluentwidgets'] = _DynamicModule('qfluentwidgets')

from app import fluent_app  # noqa: E402


def _tmp_steam(root):
    steam = root / 'steam'
    steam.mkdir(parents=True, exist_ok=True)
    return steam


class RecordsTestCase(unittest.TestCase):
    """已入库记录 存取/去重/状态检测"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='aurora_test_'))
        self.records_path = self.tmp / 'config' / 'installed_games.json'
        self._old_path = fluent_app.INSTALLED_RECORDS_PATH
        self._old_steam = fluent_app._get_steam_path_sync
        fluent_app.INSTALLED_RECORDS_PATH = self.records_path
        fluent_app._get_steam_path_sync = lambda: None

    def tearDown(self):
        fluent_app.INSTALLED_RECORDS_PATH = self._old_path
        fluent_app._get_steam_path_sync = self._old_steam
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_missing_file_returns_empty(self):
        self.assertEqual(fluent_app._load_installed_records(), [])

    def test_load_corrupt_json_returns_empty(self):
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        self.records_path.write_text('{not json', encoding='utf-8')
        self.assertEqual(fluent_app._load_installed_records(), [])

    def test_save_load_roundtrip_chinese(self):
        recs = [{"appid": "730", "name": "反恐精英2", "source": "cysaw", "dlcs": ["730001"]}]
        fluent_app._save_installed_records(recs)
        loaded = fluent_app._load_installed_records()
        self.assertEqual(loaded, recs)
        raw = self.records_path.read_text(encoding='utf-8')
        self.assertIn('反恐精英2', raw)

    def test_add_record_dedup_by_appid(self):
        fluent_app._add_installed_record(730, 'GameA', 'cysaw', ['730001'])
        fluent_app._add_installed_record('730', 'GameB', 'auto')
        recs = fluent_app._load_installed_records()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]['name'], 'GameB')
        self.assertEqual(recs[0]['dlcs'], [])

    def test_remove_record(self):
        fluent_app._add_installed_record(730, 'A', 'auto')
        fluent_app._remove_installed_record(730)
        self.assertEqual(fluent_app._load_installed_records(), [])
        fluent_app._remove_installed_record('notexist')  # 不炸

    def test_installed_appid_set_with_dlcs(self):
        recs = [
            {"appid": "730", "dlcs": ["730001", {"appid": "730002"}]},
            {"appid": "notdigit", "dlcs": None},
            {"dlcs": []},
        ]
        ids = fluent_app._installed_appid_set(recs)
        self.assertEqual(ids, {"730", "730001", "730002"})

    def test_status_record(self):
        fluent_app._add_installed_record(730, 'A', 'auto')
        self.assertEqual(fluent_app._get_existing_install_status(730), 'record')
        self.assertEqual(fluent_app._get_existing_install_status('730'), 'record')

    def test_status_dlc_record(self):
        fluent_app._add_installed_record(730, 'A', 'auto', ['999001'])
        self.assertEqual(fluent_app._get_existing_install_status(999001), 'record')

    def test_status_files(self):
        steam = _tmp_steam(self.tmp)
        (steam / 'depotcache').mkdir()
        (steam / 'depotcache' / '12345_1.manifest').write_text('x')
        fluent_app._get_steam_path_sync = lambda: steam
        self.assertEqual(fluent_app._get_existing_install_status(12345), 'files')
        # appid 前缀边界：1234 不应命中 12345 的清单
        self.assertIsNone(fluent_app._get_existing_install_status(1234))
        self.assertIsNone(fluent_app._get_existing_install_status(123456))

    def test_status_none_and_bad_input(self):
        self.assertIsNone(fluent_app._get_existing_install_status(730))
        for bad in ('', None, 'abc', '12a'):
            self.assertIsNone(fluent_app._get_existing_install_status(bad))


class ZipTargetTestCase(unittest.TestCase):
    """恢复 zip 条目路径安全检查"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='aurora_test_'))
        self.steam = _tmp_steam(self.tmp)
        self.rec = self.tmp / 'config' / 'installed_games.json'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_valid_entries(self):
        self.assertEqual(
            fluent_app._zip_entry_target('installed_games.json', self.steam, self.rec),
            self.rec)
        self.assertEqual(
            fluent_app._zip_entry_target('config.vdf', self.steam, self.rec),
            self.steam / 'config' / 'config.vdf')
        self.assertEqual(
            fluent_app._zip_entry_target('depotcache/123_1.manifest', self.steam, self.rec),
            self.steam / 'depotcache' / '123_1.manifest')
        self.assertEqual(
            fluent_app._zip_entry_target('config_depotcache/4_5.manifest', self.steam, self.rec),
            self.steam / 'config' / 'depotcache' / '4_5.manifest')
        self.assertEqual(
            fluent_app._zip_entry_target('appcache_depotcache/6_7.manifest', self.steam, self.rec),
            self.steam / 'appcache' / 'depotcache' / '6_7.manifest')

    def test_traversal_rejected(self):
        for name in ('../evil.txt', '..\\evil.txt', 'depotcache/../evil.txt',
                     'depotcache/..\\evil.txt', 'a/../../evil.txt'):
            self.assertIsNone(fluent_app._zip_entry_target(name, self.steam, self.rec), name)

    def test_absolute_and_unknown_rejected(self):
        for name in ('/etc/passwd', 'C:/evil.txt', 'C:\\evil.txt', 'other.txt',
                     'depotcache/', 'sub/installed_games.json', ''):
            self.assertIsNone(fluent_app._zip_entry_target(name, self.steam, self.rec), name)

    def test_no_steam_path_returns_none_for_steam_entries(self):
        self.assertIsNone(fluent_app._zip_entry_target('depotcache/a.manifest', None, self.rec))
        self.assertIsNone(fluent_app._zip_entry_target('config.vdf', None, self.rec))
        self.assertEqual(
            fluent_app._zip_entry_target('installed_games.json', None, self.rec), self.rec)


class SourceDisplayTestCase(unittest.TestCase):
    """来源标签显示"""

    def setUp(self):
        self._lang = fluent_app.current_language
        fluent_app.current_language = 'zh_CN'

    def tearDown(self):
        fluent_app.current_language = self._lang

    def test_display_names(self):
        self.assertEqual(fluent_app._source_display_name('auto'), '自动')
        self.assertEqual(fluent_app._source_display_name('cysaw'), 'Cysaw')
        self.assertEqual(fluent_app._source_display_name('buqiuren'), '清单不求人')
        self.assertEqual(fluent_app._source_display_name('github_auiowu'), 'GitHub')
        self.assertEqual(fluent_app._source_display_name('sac-other'), 'SAC分流')
        self.assertEqual(fluent_app._source_display_name('custom_zip_abc'), '自定义ZIP')
        self.assertEqual(fluent_app._source_display_name('unknown_src'), 'unknown_src')
        self.assertEqual(fluent_app._source_display_name(''), '未知')
        self.assertEqual(fluent_app._source_display_name(None), '未知')


class TrTestCase(unittest.TestCase):
    """多语言 key 完整性与 tr() 回退"""

    def setUp(self):
        self._lang = fluent_app.current_language
        fluent_app.current_language = 'zh_CN'

    def tearDown(self):
        fluent_app.current_language = self._lang

    def test_all_langs_have_new_feature_keys(self):
        new_keys = set(fluent_app._NEW_FEATURE_TEXTS['zh_CN'].keys())
        for lang, texts in fluent_app.TEXTS.items():
            missing = new_keys - set(texts.keys())
            self.assertFalse(missing, f"lang={lang} missing: {missing}")

    def test_tr_fallback_and_format(self):
        self.assertEqual(fluent_app.tr('batch_install'), '批量入库')
        self.assertEqual(
            fluent_app.tr('already_installed', 730, '记录中'),
            'AppID 730 已入库（记录中），已跳过')
        fluent_app.current_language = 'en_US'
        self.assertEqual(fluent_app.tr('batch_install'), 'Batch Install')
        # 无翻译的语言回退 zh_CN
        self.assertEqual(fluent_app.tr('batch_install_placeholder'), 'batch_install_placeholder')


class FindFnameTestCase(unittest.TestCase):
    """trainer_backend._find_fname 净化"""

    def setUp(self):
        from backend import trainer_backend
        self._find_fname = trainer_backend._find_fname

    def _resp(self, cd, url='https://example.com/files/trainer.zip'):
        class Resp:
            pass
        r = Resp()
        r.headers = {} if cd is None else {'content-disposition': cd}
        r.url = url
        return r

    def test_plain_filename(self):
        self.assertEqual(self._find_fname(self._resp('attachment; filename=game.zip')), 'game.zip')
        self.assertEqual(self._find_fname(self._resp('attachment; filename="game.zip"')), 'game.zip')

    def test_filename_star_utf8(self):
        r = self._resp("attachment; filename*=UTF-8''%E6%B8%B8%E6%88%8F.zip")
        self.assertEqual(self._find_fname(r), '游戏.zip')

    def test_path_traversal_sanitized(self):
        self.assertEqual(self._find_fname(self._resp('attachment; filename=..\\..\\evil.zip')), 'evil.zip')
        self.assertEqual(self._find_fname(self._resp('attachment; filename=../../evil.zip')), 'evil.zip')
        self.assertEqual(self._find_fname(self._resp('attachment; filename=..\\evil.zip')), 'evil.zip')

    def test_illegal_chars_removed(self):
        self.assertEqual(self._find_fname(self._resp('attachment; filename=a<b>c:d|e?f*.zip')), 'abcdef.zip')

    def test_no_cd_falls_back_to_url(self):
        r = self._resp(None, 'https://example.com/files/trainer%20x.zip')
        self.assertEqual(self._find_fname(r), 'trainer x.zip')

    def test_empty_falls_back(self):
        self.assertEqual(self._find_fname(self._resp('attachment; filename=')), 'trainer.zip')
        self.assertEqual(self._find_fname(self._resp(None, 'https://example.com/')), 'trainer.zip')
        self.assertEqual(self._find_fname(self._resp('attachment; filename=a:*?')), 'trainer.zip')


class CompareVersionsTestCase(unittest.TestCase):
    """cai_backend._compare_versions"""

    def setUp(self):
        from backend import cai_backend
        self.cmp = cai_backend.CaiBackend._compare_versions
        self.obj = object.__new__(cai_backend.CaiBackend)

    def test_compare(self):
        self.assertEqual(self.cmp(self.obj, '1.0', '2.0'), -1)
        self.assertEqual(self.cmp(self.obj, '2.7', '1.0'), 1)
        self.assertEqual(self.cmp(self.obj, '1.0', '1.0'), 0)
        self.assertEqual(self.cmp(self.obj, '1.0.1', '1.0'), 1)
        self.assertEqual(self.cmp(self.obj, '1.0', '1.0.1'), -1)
        self.assertEqual(self.cmp(self.obj, '1.0.0', '1.0'), 0)
        # 空后缀视为正式版，高于带后缀
        self.assertEqual(self.cmp(self.obj, '1.0', '1.0-beta'), 1)
        self.assertEqual(self.cmp(self.obj, '1.0-beta', '1.0'), -1)
        # 非版本字符串按 0.0.0 参与比较（不崩溃）
        self.assertEqual(self.cmp(self.obj, 'abc', '1.0'), -1)
        self.assertEqual(self.cmp(self.obj, '1.0', 'abc'), 1)


if __name__ == '__main__':
    unittest.main()
