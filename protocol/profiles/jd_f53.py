PROFILE_KEY = 'jd_f53'
PROFILE_NAME = 'JD-F53'
TYPE_ORIGIN_LABEL = '厂商扩展'

# 源地址和目标地址的字节序：金盾 F53 未遵循国标小端序规范，实际使用大端序（高字节在前）
ADDR_BYTE_ORDER = 'big'

PROFILE_NOTES = [
    '源地址和目标地址采用大端序（高字节在前），与国标 GB/T 26875.3 规定的小端序不同，这是该厂商的实际行为。',
]