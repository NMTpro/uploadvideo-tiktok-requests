import os
import sys
import base64
import random
import threading
from io import BytesIO
from db import SessionDB
import json
import time
import datetime
from urllib.parse import urlencode
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    import requests
    from PIL import Image, ImageDraw, ImageFont
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QPushButton, QVBoxLayout,
        QDialog, QLabel, QMessageBox, QScrollArea, QFrame, QHBoxLayout, QLineEdit, QFileDialog
)
    from PyQt5.QtGui import QPixmap, QImage
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
    from PIL import Image, ImageDraw, ImageFont
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QPushButton, QVBoxLayout,
        QDialog, QLabel, QMessageBox
    )
    from PyQt5.QtGui import QPixmap, QImage
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
except:
    os.system('pip install requests Pillow PyQt5')
    import requests
    from PIL import Image, ImageDraw, ImageFont
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QPushButton, QVBoxLayout,
        QDialog, QLabel, QMessageBox
    )
    from PyQt5.QtGui import QPixmap, QImage
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
    from PIL import Image, ImageDraw, ImageFont
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QPushButton, QVBoxLayout,
        QDialog, QLabel, QMessageBox, QScrollArea, QFrame, QHBoxLayout, QLineEdit, QFileDialog
    )
    from PyQt5.QtGui import QPixmap, QImage
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
from x_bogus_ import get_x_bogus
from util import assertSuccess, printError, getTagsExtra, uploadToTikTok, getCreationId
class BotSignals(QObject):
    message_signal = pyqtSignal(str)

bot_signals = BotSignals()

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36'

def log(msg):
    bot_signals.message_signal.emit(msg)


def uploadVideo(session_id, video, title, tags, users=[], url_prefix="www", schedule_time: int = 0, proxy: dict = None):
    tiktok_min_margin_schedule_time =  900  # 15 minutes
    tiktok_max_margin_schedule_time = 864000  # 10 days
    margin_to_upload_video = 300  # 5 minutes

    now_utc = datetime.datetime.now(datetime.timezone.utc).timestamp()
    min_schedule_time = now_utc + tiktok_min_margin_schedule_time + margin_to_upload_video
    max_schedule_time = now_utc + tiktok_max_margin_schedule_time

    if schedule_time == 0:
        pass
    elif schedule_time < min_schedule_time:
        print(f"[-] Can not schedule video in less than {(tiktok_min_margin_schedule_time + margin_to_upload_video) // 60} minutes")
        return False
    elif schedule_time > max_schedule_time:
        print(f"[-] Can not schedule video in more than {tiktok_max_margin_schedule_time // 86400} days")
        return False

    session = requests.Session()

    if proxy:
        session.proxies.update(proxy)
    session.cookies.set("sessionid", session_id, domain=".tiktok.com")
    session.verify = True
    headers = {
        'User-Agent': UA
    }
    url = f"https://{url_prefix}.tiktok.com/upload/"
    r = session.get(url, headers=headers)
    if not assertSuccess(url, r):
        return False
    creationid = getCreationId()
    url = f"https://{url_prefix}.tiktok.com/api/v1/web/project/create/?creation_id={creationid}&type=1&aid=1988"
    headers = {
        "X-Secsdk-Csrf-Request": "1",
        "X-Secsdk-Csrf-Version": "1.2.8"
    }
    r = session.post(url, headers=headers)
    if not assertSuccess(url, r):
        return False
    try:
        tempInfo = r.json()['project']
    except KeyError:
        print(f"[-] An error occured while reaching {url}")
        print("[-] Please try to change the --url_server argument to the adapted prefix for your account")
        return False
    creationID = tempInfo["creationID"]
    projectID = tempInfo["project_id"]
    url = f"https://{url_prefix}.tiktok.com/passport/web/account/info/"
    r = session.get(url)
    if not assertSuccess(url, r):
        return False
    # user_id = r.json()["data"]["user_id_str"]
    log("Start uploading video")
    video_id = uploadToTikTok(video, session)
    if not video_id:
        log("Video upload failed")
        return False
    log("Video uploaded successfully")
    time.sleep(2)
    result = getTagsExtra(title, tags, users, session, url_prefix)
    time.sleep(3)
    title = result[0]
    text_extra = result[1]
    postQuery = {
        'app_name': 'tiktok_web',
        'channel': 'tiktok_web',
        'device_platform': 'web',
        'aid': 1988
    }
    data = {
        "post_common_info": {
            "creation_id": creationID,
            "enter_post_page_from": 1,
            "post_type": 3
        },
        "feature_common_info_list": [
            {
                "geofencing_regions": [],
                "playlist_name": "",
                "playlist_id": "",
                "tcm_params": "{\"commerce_toggle_info\":{}}",
                "sound_exemption": 0,
                "anchors": [],
                "vedit_common_info": {
                    "draft": "",
                    "video_id": video_id
                },
                "privacy_setting_info": {
                    "visibility_type": 0,
                    "allow_duet": 1,
                    "allow_stitch": 1,
                    "allow_comment": 1
                }
            }
        ],
        "single_post_req_list": [
            {
                "batch_index": 0,
                "video_id": video_id,
                "is_long_video": 0,
                "single_post_feature_info": {
                    "text": title,
                    "text_extra": text_extra,
                    "markup_text": title,
                    "music_info": {},
                    "poster_delay": 0,
                }
            }
        ]
    }
    if schedule_time == 0:
        pass
    elif schedule_time > min_schedule_time:
        data["upload_param"]["schedule_time"] = schedule_time
    else:
        log(f"Video schedule time is less than {tiktok_min_margin_schedule_time // 60} minutes in the future, the upload process took more than"
            f"the {margin_to_upload_video // 60} minutes of margin to upload the video")
        return False
    postQuery['X-Bogus'] = get_x_bogus(urlencode(postQuery), json.dumps(data, separators=(',', ':')), UA)
    url = f'https://{url_prefix}.tiktok.com/tiktok/web/project/post/v1/'
    headers = {
        'Host': f'{url_prefix}.tiktok.com',
        'content-type': 'application/json',
        'user-agent': UA,
        'origin': 'https://www.tiktok.com',
        'referer': 'https://www.tiktok.com/'
    }
    r = session.post(url, params=postQuery, data=json.dumps(data, separators=(',', ':')), headers=headers)
    if not assertSuccess(url, r):
        log("Publish failed")
        printError(url, r)
        return False
    if r.json()["status_code"] == 0:
        log(f"Published successfully {'| Scheduled for ' + str(schedule_time) if schedule_time else ''}")
    else:
        log("Publish failed")
        printError(url, r)
        return False

    return True

def gen(qr_data_b64: str, t: str = '') -> Image.Image:
    """
    Nhận vào chuỗi Base64 (PNG/JPEG) của QR, trả về PIL.Image đã xử lý:
    - Chuyển màu nền trắng thành đen
    - Đổi màu đen thành màu ngẫu nhiên
    - Vẽ text "t.me/@haglooo" lên ảnh
    """
    # Giải mã Base64 và mở thành PIL Image
    qr_bytes = base64.b64decode(qr_data_b64)
    img = Image.open(BytesIO(qr_bytes)).convert("RGB")
    width, height = img.size

    # Tạo màu ngẫu nhiên
    hex_digits = "0123456789abcdef"
    hex_code = "#" + "".join(random.choices(hex_digits, k=6))
    rgb_code = tuple(int(hex_code[i:i+2], 16) for i in (1, 3, 5))

    # Đổi màu
    pixels = img.load()
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]
            if (r, g, b) == (255, 255, 255):
                pixels[x, y] = (0, 0, 0)
            elif (r, g, b) == (0, 0, 0):
                pixels[x, y] = rgb_code

    # Vẽ text vào vị trí cố định
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("font.ttf", 25)
    except IOError:
        # Nếu không có font.ttf, dùng font mặc định
        font = ImageFont.load_default()
    position = (150, height - 35)
    if t:
        draw.text(position, t, font=font, fill=(255, 255, 255))
    else:
        draw.text(position, "Nguyễn Minh Tâm", font=font, fill=(255, 255, 255))

    return img

# --- QThread để fetch QR và poll kết quả ---
class QRWorker(QThread):
    qr_ready    = pyqtSignal(QImage)   # phát khi QR sẵn sàng
    login_ok    = pyqtSignal(str, str, str)      # phát khi có sessionid
    scanned = pyqtSignal()
    ok = True

    def run(self):
        session = requests.Session()
        # --- 1) Lấy QR + token ---
        url_get = "https://api16-normal-c-useast1a.tiktokv.com/passport/mobile/get_qrcode/?service=https%3A%2F%2Ftv.tiktok.com&account_sdk_source=app&passport-sdk-version=17&os_api=25&device_type=ASUS_Z01QD&ssmix=a&manifest_version_code=110908&dpi=240&carrier_region=DE&uoo=0&region=DE&app_name=tiktok_tv&version_name=11.9.8&timezone_offset=3600&ts=1680968776&ab_version=11.9.8&pass-route=1&cpu_support64=true&pass-region=1&storage_type=1&ac2=wifi&ac=wifi&app_type=normal&host_abi=armeabi-v7a&channel=googleplay&update_version_code=110908&_rticket=1680968776053&device_platform=android&iid=7219304446219192070&build_number=11.9.8&locale=de_DE&op_region=DE&version_code=110908&timezone_name=Europe%2FBerlin&cdid=f03bebda-f46d-48ac-a48c-94c3be811ac2&openudid=d8e48a4690fded4b&sys_region=DE&device_id=7191957835704632838&app_language=de&resolution=1280*720&device_brand=Asus&language=de&os_version=7.1.2&aid=4082&okhttp_version=4.0.71.6-tiktok"
        # (giải ngắn cho dễ đọc; bạn gán lại đầy đủ như biến `url` của bạn)
        headers = {
            "accept-encoding": "gzip",
            "connection": "Keep-Alive",
            "cookie": "store-idc=maliva; store-country-code=de; store-country-code-src=did; install_id=7219304446219192070; ttreq=1$61d3b081ce60c998b44f7b7190d5c3006ef38e90; odin_tt=b3d2f53798a67f4f047cfb9ffc40bcc738db759ef09452d06e0a9b19457ea8cad201edc274985908614eb37b8b6bb980a2d8153f700aefd6de7752b84a0e2e44a28c2cf70c02f91d4602a8551ad49ee9; passport_csrf_token=73325592c16331165e9aa4173fb5a3cd; passport_csrf_token_default=73325592c16331165e9aa4173fb5a3cd; msToken=-FKWjXsLY02ElQb95HnVFhQJnYt1FkV7uTTeZ8q56ALTOWmwPBf2hMqSIdPb4NzB-8gjZ1-NaKy1oGSFCyyrh5bMqGmQVC-m-3LJ1ID3w6yMqEWiK5lewNec",
            "host": "api16-normal-c-useast1a.tiktokv.com",
            "passport-sdk-version": "17",
            "sdk-version": "2",
            "user-agent": "com.tiktok.tv/110908 (Linux; U; Android 7.1.2; de_DE; ASUS_Z01QD; Build/N2G48H;tt-ok/3.10.0.2)",
            "x-gorgon": "040480aa400071b467ddbfce4d8e00fb639ee8273914aaa0ece7",
            "x-khronos": "1680968776",
            "x-ss-req-ticket": "1680968776054",
            "x-tt-passport-csrf-token": "73325592c16331165e9aa4173fb5a3cd",
            "x-tt-store-region": "de",
            "x-tt-store-region-did": "de",
            "x-tt-store-region-src": "did",
            "x-tt-store-region-uid": "",
        }

        resp = session.get(url_get, headers=headers).json()
        qr_b64 = resp["data"]["qrcode"]
        token  = resp["data"]["token"]

        # Sinh PIL→QImage và emit
        pil_img = gen(qr_b64)
        buf = BytesIO(); pil_img.save(buf, format="PNG")
        qimg = QImage.fromData(buf.getvalue())
        self.qr_ready.emit(qimg)

        # --- 2) Poll check until login ---
        url_check_tpl = f"https://api16-normal-c-useast1a.tiktokv.com/passport/mobile/check_qrconnect/?token={token}&service=https%3A%2F%2Ftv.tiktok.com&account_sdk_source=app&passport-sdk-version=17&os_api=25&device_type=ASUS_Z01QD&ssmix=a&manifest_version_code=110908&dpi=240&carrier_region=DE&uoo=0&region=DE&app_name=tiktok_tv&version_name=11.9.8&timezone_offset=3600&ts=1680969476&ab_version=11.9.8&pass-route=1&cpu_support64=true&pass-region=1&storage_type=1&ac2=wifi&ac=wifi&app_type=normal&host_abi=armeabi-v7a&channel=googleplay&update_version_code=110908&_rticket=1680969476413&device_platform=android&iid=7219304446219192070&build_number=11.9.8&locale=de_DE&op_region=DE&version_code=110908&timezone_name=Europe%2FBerlin&cdid=f03bebda-f46d-48ac-a48c-94c3be811ac2&openudid=d8e48a4690fded4b&sys_region=DE&device_id=7191957835704632838&app_language=de&resolution=1280*720&device_brand=Asus&language=de&os_version=7.1.2&aid=4082&okhttp_version=4.0.71.6-tiktok"
        while True:
            if not self.ok:
                return
            try:
                r = session.get(url_check_tpl, headers=headers)
                text = r.text
                if "scanned" in text:
                    self.scanned.emit()
                    # print('Quét QR Thành Công Chờ Xác Nhận Trên App')
                if "session_key" in text:
                    # trích sessionid từ cookie
                    cookie_str = str(r.cookies)
                    print(cookie_str)
                    sessionid = cookie_str.split("sessionid=")[1].split(" ")[0]
                    url = 'https://api16-normal-c-alisg.tiktokv.com/passport/account/info/v2/?scene=normal&multi_login=1&account_sdk_source=app&passport-sdk-version=19&os_api=25&device_type=A5010&ssmix=a&manifest_version_code=2018093009&dpi=191&carrier_region=JO&uoo=1&region=US&app_name=musical_ly&version_name=7.1.2&timezone_offset=28800&ts=1628767214&ab_version=7.1.2&residence=SA&cpu_support64=false&current_region=JO&ac2=wifi&ac=wifi&app_type=normal&host_abi=armeabi-v7a&channel=googleplay&update_version_code=2018093009&_rticket=1628767221573&device_platform=android&iid=7396386396296286392&build_number=7.1.2&locale=en&op_region=SA&version_code=200705&timezone_name=Asia%2FShanghai&cdid=f61ca549-c9ee-450b-90da-8854423b74e7&openudid=3e5afbd3f6dde322&sys_region=US&device_id=7296396296396396393&app_language=vi&resolution=576*1024&device_brand=OnePlus&language=vi&os_version=7.1.2&aid=1233&mcc_mnc=2947'
                    headers={'Host': 'api16-normal-c-alisg.tiktokv.com', 'Cookie': 'sessionid='+sessionid,'Accept-Encoding': 'gzip, deflate',
                                        'User-Agent': 'com.zhiliaoapp.musically/2022107060 (Linux; U; Android 7.1.2; en_US; G011A; Build/N2G48H;tt-ok/3.10.0.2)'}
                    re = requests.get(url, headers=headers).json()
                    username = re['data']['username']
                    user_id = re['data']['user_id']
                    self.login_ok.emit(sessionid, str(username), str(user_id))
                    return
                self.msleep(10)  # đợi 1s rồi poll lại
            except:
                continue

class QRDialog(QDialog):
    def __init__(self, qimage: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quét QR Login TikTok")
        pix = QPixmap.fromImage(qimage)
        self.setFixedSize(pix.width(), pix.height() + 40)

        # 1) Ảnh QR
        self.lbl_img = QLabel(self)
        self.lbl_img.setPixmap(pix)
        self.lbl_img.setAlignment(Qt.AlignCenter)
        # 2) Message dưới QR
        self.lbl_msg = QLabel("Quét QR Để Login-TikTok", self)
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        self.lbl_msg.setStyleSheet(
            "font-size: 18px;"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.lbl_img)
        lay.addWidget(self.lbl_msg)

    def set_message(self, text: str):
        self.lbl_msg.setText(text)
        self.lbl_msg.setStyleSheet(
            "color: #2196F3; "  # xanh dương
            "font-weight: bold; "
            "font-size: 18px; "
            "padding: 5px;"
        )
        self.lbl_img.setVisible(False)

# --- MainWindow ---
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tool TikTok NMTpro")
        self.resize(500, 300)

        # Khởi tạo DB
        self.db = SessionDB()

        # Layout chính
        main_layout = QVBoxLayout(self)

        # Scroll area chứa danh sách sessions
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.session_container = QWidget()
        self.session_layout = QVBoxLayout(self.session_container)
        self.scroll.setWidget(self.session_container)
        main_layout.addWidget(self.scroll)

        # Nút quét QR
        self.btn = QPushButton("Quét QR & Thêm tài khoản", self)
        self.btn.clicked.connect(self.start_worker)
        main_layout.addWidget(self.btn)

        # Hiển thị danh sách hiện có
        self.load_sessions()
        bot_signals.message_signal.connect(self.update_label_table)
        # ——— Chèn status bar ở đây ———
        self.status_label = QLabel("", self)
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setStyleSheet("color: #555; padding: 4px;")
        main_layout.addWidget(self.status_label)

    def update_label_table(self, msg):
        self.status_label.setText(f"<span style='color:#2196F3; font-size:14px; font-weight:bold'>{msg}</span>")

    def load_sessions(self):
        for i in reversed(range(self.session_layout.count())):
            widget = self.session_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        rows = self.db.fetch_all()
        if not rows:
            lbl = QLabel("Chưa có tài khoản nào.", self.session_container)
            self.session_layout.addWidget(lbl)
        else:
            for r in rows:
                # Tạo dòng với label và nút Upload
                frame = QFrame()
                frame.setFrameShape(QFrame.StyledPanel)
                hl = QHBoxLayout(frame)
                text = f"@{r['username']} | ID: {r['user_id']} | {r['timestamp']}"
                # Hiển thị HTML cho đẹp
                html = (
                    f"<div style='padding:4px;'>"
                    f"<span style='color:#2196F3; font-weight:bold;'>@{r['username']}</span> "
                    f"<span style='color:#555;'>| ID: {r['user_id']}</span> "
                    f"<span style='color:#888; font-size:10px;'>{r['timestamp']}</span>"
                    f"</div>"
                )
                lbl = QLabel(html, frame)
                lbl.setTextFormat(Qt.RichText)
                btn_upload = QPushButton("Upload", frame)
                # Lấy sessionid từ record và kết nối hàm upload
                sid = r['sessionid']
                btn_upload.clicked.connect(lambda _, s=sid: self.upload_session(s))
                hl.addWidget(lbl)
                hl.addStretch()
                hl.addWidget(btn_upload)
                self.session_layout.addWidget(frame)

    def upload_session(self, sessionid):
        """
        Mở dialog để chọn video MP4, nhập nội dung, hashtag, gắn thẻ và đăng.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Upload Video")
        layout = QVBoxLayout(dlg)

        # Chọn file MP4
        file_layout = QHBoxLayout()
        btn_choose = QPushButton("Chọn file MP4", dlg)
        line_path = QLineEdit(dlg)
        line_path.setReadOnly(True)
        btn_choose.clicked.connect(lambda: self.choose_file(line_path))
        file_layout.addWidget(btn_choose)
        file_layout.addWidget(line_path)
        layout.addLayout(file_layout)

        # Nội dung video
        line_content = QLineEdit(dlg)
        line_content.setPlaceholderText("Nội dung video")
        layout.addWidget(line_content)

        # Hashtag
        line_hashtag = QLineEdit(dlg)
        line_hashtag.setPlaceholderText("Hashtag (ví dụ: fun tiktok)")
        layout.addWidget(line_hashtag)

        # Gắn thẻ tên
        line_tag = QLineEdit(dlg)
        line_tag.setPlaceholderText("Gắn thẻ tên (ví dụ: username1 username2)")
        layout.addWidget(line_tag)

        # Nút đăng video
        btn_post = QPushButton("Đăng video", dlg)
        btn_post.clicked.connect(
            lambda: self.post_video(
                sessionid,
                line_path.text(),
                line_content.text(),
                line_hashtag.text(),
                line_tag.text(),
                dlg
            )
        )
        layout.addWidget(btn_post)

        dlg.setLayout(layout)
        dlg.exec_()

    def choose_file(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn video MP4", "", "Video Files (*.mp4)")
        if path:
            line_edit.setText(path)

    def post_video(self, sessionid, filepath, content, hashtag, tag, dialog):

        print(f"Uploading {filepath} with session={sessionid}")
        print(f"Content: {content}, Hashtag: {hashtag}, Tag: {tag}")
        threading.Thread(target=uploadVideo, args=(sessionid, filepath, content, hashtag.split(), tag.split(), ), daemon=True).start()
        dialog.accept()

    def start_worker(self):
        self.btn.setEnabled(False)
        self.worker = QRWorker()
        self.worker.qr_ready.connect(self.show_qr)
        self.worker.scanned.connect(self.on_scanned)
        self.worker.login_ok.connect(self.on_login)
        self.worker.start()

    def show_qr(self, qimg: QImage):
        self.dlg = QRDialog(qimg, self)
        self.dlg.finished.connect(self.on_qr_closed)
        self.dlg.show()

    def on_qr_closed(self):
        self.worker.ok = False
        self.worker = None
        self.btn.setEnabled(True)

    def on_scanned(self):
        if hasattr(self, 'dlg'):
            self.dlg.set_message("Quét thành công – Chờ xác nhận trên app TikTok")

    def on_login(self, sessionid: str, username: str, user_id: str):
        QMessageBox.information(self, "Success",
                                f"Logged in! @{username}|{user_id}")
        self.btn.setEnabled(True)
        if hasattr(self, 'dlg'):
            self.dlg.close()
        try:
            self.db.insert_session(sessionid, username, user_id)
            print(f"Đã lưu sessionid vào DB: {sessionid}")
        except Exception as e:
            print(f"Lỗi khi lưu sessionid vào DB: {e}")
        # Cập nhật lại giao diện
        self.load_sessions()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
