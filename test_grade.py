# Code mẫu thử nghiệm hệ thống quản lý lớp học
def tinh_diem_trung_binh(diem_toan, diem_van):
    return (diem_toan + diem_van) / 2

# Chạy thử
toan = 8.5
van = 7.5
dtb = tinh_diem_trung_binh(toan, van)

print(f"Điểm Toán: {toan} | Điểm Văn: {van}")
print(f"=> Điểm trung bình của học sinh là: {dtb}")