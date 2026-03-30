"""
测试配置系统
"""
import pytest
from yinian.core.config import Config, get_config, get_config_dir


class TestConfig:
    """配置测试"""
    
    def test_config_dir_creation(self):
        """测试配置目录创建"""
        config = Config()
        assert config.config_dir.exists()
        assert config.cache_dir.exists()
        assert config.sessions_dir.exists()
    
    def test_get_set(self):
        """测试配置读取和设置"""
        config = Config()
        
        # 测试默认值
        assert config.get("defaults.model") == "deepseek"
        
        # 测试设置
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"
        
        # 测试点号路径
        config.set("test.nested.value", 123)
        assert config.get("test.nested.value") == 123
    
    def test_model_config(self):
        """测试模型配置"""
        config = Config()
        
        # 获取默认模型
        default_model = config.get_default_model()
        assert default_model == "deepseek"
        
        # 列出可用模型
        models = config.list_models()
        assert "deepseek" in models
    
    def test_api_key_management(self):
        """测试 API Key 管理"""
        config = Config()
        
        # 设置 API Key
        test_key = "sk-test-key-12345"
        config.set_api_key("deepseek", test_key)
        
        # 获取 API Key
        retrieved_key = config.get_api_key("deepseek")
        assert retrieved_key == test_key
        
        # 清理测试 Key
        config.set_api_key("deepseek", "")
    
    def test_global_config_instance(self):
        """测试全局配置实例"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2  # 应该是同一个实例


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
