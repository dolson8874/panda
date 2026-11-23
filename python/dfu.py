import os
import usb1
import struct

from .base import BaseSTBootloaderHandle
from .spi import STBootloaderSPIHandle, PandaSpiException
from .usb import STBootloaderUSBHandle
from .constants import FW_PATH, McuType


class PandaDFU:
  def __init__(self, dfu_serial: str | None, usb_port: tuple[int, tuple[int, ...]] | None = None):
    # try USB, then SPI
    handle: BaseSTBootloaderHandle | None
    self._context, handle = PandaDFU.usb_connect(dfu_serial, usb_port=usb_port)
    if handle is None and usb_port is None:
      if self._context is not None:
        self._context.close()
      self._context, handle = PandaDFU.spi_connect(dfu_serial)

    if handle is None:
      if self._context is not None:
        self._context.close()
      raise Exception(f"failed to open DFU device {dfu_serial}")

    self._handle: BaseSTBootloaderHandle = handle
    self._mcu_type: McuType = self._handle.get_mcu_type()

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.close()

  def close(self):
    if self._handle is not None:
      self._handle.close()
      self._handle = None
      if self._context is not None:
        self._context.close()

  @staticmethod
  def usb_connect(dfu_serial: str | None, usb_port=None):
    handle = None
    context = usb1.USBContext()
    context.open()
    for device in context.getDeviceList(skip_on_error=True):
      if usb_port is not None and (device.getBusNumber(), tuple(device.getPortNumberList())) != usb_port:
        continue
      if device.getVendorID() == 0x0483 and device.getProductID() == 0xdf11:
        try:
          this_dfu_serial = device.open().getASCIIStringDescriptor(3)
        except Exception:
          continue

        if this_dfu_serial == dfu_serial or dfu_serial is None:
          handle = STBootloaderUSBHandle(device, device.open())
          break

    return context, handle

  @staticmethod
  def spi_connect(dfu_serial: str | None):
    handle = None
    this_dfu_serial = None

    try:
      handle = STBootloaderSPIHandle()
      this_dfu_serial = PandaDFU.st_serial_to_dfu_serial(handle.get_uid(), handle.get_mcu_type())
    except PandaSpiException:
      handle = None

    if dfu_serial is not None and dfu_serial != this_dfu_serial:
      handle = None

    return None, handle

  @staticmethod
  def usb_list(usb_port=None) -> list[str]:
    dfu_serials = []
    try:
      with usb1.USBContext() as context:
        for device in context.getDeviceList(skip_on_error=True):
          if usb_port is not None and (device.getBusNumber(), tuple(device.getPortNumberList())) != usb_port:
            continue
          if device.getVendorID() == 0x0483 and device.getProductID() == 0xdf11:
            try:
              dfu_serials.append(device.open().getASCIIStringDescriptor(3))
            except Exception:
              pass
    except Exception:
      pass
    return dfu_serials

  @staticmethod
  def spi_list() -> list[str]:
    try:
      _, h = PandaDFU.spi_connect(None)
      if h is not None:
        dfu_serial = PandaDFU.st_serial_to_dfu_serial(h.get_uid(), h.get_mcu_type())
        return [dfu_serial, ]
    except PandaSpiException:
      pass
    return []

  @staticmethod
  def st_serial_to_dfu_serial(st: str, mcu_type: McuType = McuType.H7):
    if st is None or st == "none":
      return None
    try:
      uid_base = struct.unpack("H" * 6, bytes.fromhex(st))
      offset = 0xA if mcu_type == McuType.F4 else 0
      serial = struct.pack("!HHH", (uid_base[1] + uid_base[5]) & 0xFFFF, (uid_base[0] + uid_base[4] + offset) & 0xFFFF, uid_base[3])
      return serial.hex().upper()
    except struct.error:
      return None

  def get_mcu_type(self) -> McuType:
    return self._mcu_type

  def reset(self):
    self._handle.jump(self._mcu_type.config.bootstub_address)

  def program_bootstub(self, code_bootstub):
    self._handle.clear_status()

    # erase bootstub + app sectors
    for i in (0, 1):
      self._handle.erase_sector(i)

    # write bootstub
    self._handle.program(self._mcu_type.config.bootstub_address, code_bootstub)

  def recover(self):
    fn = os.path.join(FW_PATH, self._mcu_type.config.bootstub_fn)
    with open(fn, "rb") as f:
      code = f.read()
    self.program_bootstub(code)
    self.reset()

  @staticmethod
  def list() -> list[str]:
    ret = PandaDFU.usb_list()
    ret += PandaDFU.spi_list()
    return list(set(ret))
