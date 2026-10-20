from core.utils.text_processing import apply_gbk_compatibility


def test_gbk_compatibility_preserves_em_dash_codepoint():
    assert apply_gbk_compatibility("破折号—后文") == "破折号—后文"
    assert ord(apply_gbk_compatibility("—")) == 0x2014


def test_gbk_compatibility_keeps_other_legacy_substitutions():
    assert apply_gbk_compatibility("・ー♪~⋯≫≪⇒") == "·―～～…》《→"
