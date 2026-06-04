"""
Phase 61 - 物联网设备管理测试
验证设备注册、状态监控、数据采集和指令下发功能是否正常工作
"""
import unittest
from src.utils.iot_manager import (
    DeviceManager,
    Device,
    SensorReading,
    DeviceStatus,
    get_device_manager
)


class TestDeviceManager(unittest.TestCase):
    """设备管理器测试"""

    def setUp(self):
        """测试前设置"""
        self.manager = DeviceManager()

    def test_register_device(self):
        """测试注册设备"""
        device = Device("dev-1", "Temperature Sensor", "sensor")
        result = self.manager.register_device(device)
        self.assertTrue(result)
        self.assertIsNotNone(self.manager.get_device("dev-1"))

    def test_unregister_device(self):
        """测试注销设备"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        result = self.manager.unregister_device("dev-1")
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_device("dev-1"))

    def test_update_status(self):
        """测试更新状态"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        result = self.manager.update_device_status("dev-1", DeviceStatus.ONLINE)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_device("dev-1").status, DeviceStatus.ONLINE)

    def test_get_devices_by_status(self):
        """测试按状态获取设备"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        self.manager.register_device(Device("dev-2", "Sensor"))
        self.manager.update_device_status("dev-1", DeviceStatus.ONLINE)
        self.manager.update_device_status("dev-2", DeviceStatus.OFFLINE)

        online = self.manager.get_devices_by_status(DeviceStatus.ONLINE)
        self.assertEqual(len(online), 1)
        self.assertEqual(online[0].device_id, "dev-1")

    def test_get_devices_by_type(self):
        """测试按类型获取设备"""
        self.manager.register_device(Device("dev-1", "Sensor", "temperature"))
        self.manager.register_device(Device("dev-2", "Sensor", "humidity"))

        temp = self.manager.get_devices_by_type("temperature")
        self.assertEqual(len(temp), 1)

    def test_add_reading(self):
        """测试添加读数"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        reading = SensorReading("dev-1", "temperature", 25.5, "C")
        result = self.manager.add_reading(reading)
        self.assertTrue(result)

    def test_get_readings(self):
        """测试获取读数"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        self.manager.add_reading(SensorReading("dev-1", "temperature", 20.0, "C"))
        self.manager.add_reading(SensorReading("dev-1", "temperature", 25.0, "C"))
        self.manager.add_reading(SensorReading("dev-1", "humidity", 60.0, "%"))

        readings = self.manager.get_readings("dev-1", "temperature")
        self.assertEqual(len(readings), 2)

    def test_get_latest_reading(self):
        """测试获取最新读数"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        self.manager.add_reading(SensorReading("dev-1", "temperature", 20.0, "C"))
        self.manager.add_reading(SensorReading("dev-1", "temperature", 25.0, "C"))

        latest = self.manager.get_latest_reading("dev-1", "temperature")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.value, 25.0)

    def test_callback(self):
        """测试回调"""
        readings = []

        def callback(reading):
            readings.append(reading)

        self.manager.add_callback(callback)
        self.manager.register_device(Device("dev-1", "Sensor"))
        self.manager.add_reading(SensorReading("dev-1", "temperature", 25.0, "C"))

        self.assertEqual(len(readings), 1)

    def test_send_command_online(self):
        """测试发送命令到在线设备"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        self.manager.update_device_status("dev-1", DeviceStatus.ONLINE)
        result = self.manager.send_command("dev-1", "reboot")
        self.assertTrue(result)

    def test_send_command_offline(self):
        """测试发送命令到离线设备"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        result = self.manager.send_command("dev-1", "reboot")
        self.assertFalse(result)

    def test_stats(self):
        """测试统计"""
        self.manager.register_device(Device("dev-1", "Sensor"))
        self.manager.register_device(Device("dev-2", "Sensor"))
        self.manager.update_device_status("dev-1", DeviceStatus.ONLINE)
        self.manager.add_reading(SensorReading("dev-1", "temp", 25.0, "C"))

        stats = self.manager.get_stats()
        self.assertEqual(stats["total_devices"], 2)
        self.assertEqual(stats["online"], 1)
        self.assertEqual(stats["total_readings"], 1)


class TestGlobalInstance(unittest.TestCase):
    """全局实例测试"""

    def test_get_device_manager(self):
        """测试获取全局管理器"""
        m1 = get_device_manager()
        m2 = get_device_manager()
        self.assertIs(m1, m2)


def run_tests():
    """运行测试"""
    print("=" * 60)
    print("Phase 61 - 物联网设备管理测试")
    print("=" * 60)

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDeviceManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalInstance))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tests()
