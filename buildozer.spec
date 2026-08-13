[app]

# ============================================
# 기본 정보
# ============================================

title = LDR Template

package.name = ldrtemplate
package.domain = org.ldr

source.dir = .

# 포함할 확장자
#  - png       : assets/Template.png
#  - ttf       : 한글 폰트 (추가 시 대비)
#  - json      : 설정/데이터 파일 (없으면 무해)
source.include_exts = py,png,jpg,jpeg,ttf,atlas,json

# 포함할 폴더 (없으면 무시됨)
source.include_patterns = assets/*,core/*

# 제외
source.exclude_dirs = tests,bin,.buildozer,__pycache__,sample,.github
source.exclude_patterns = *.txt,license,buildozer.spec

version = 0.1


# ============================================
# 의존성
#   pyjnius : filesource.py 의 autoclass (권한 확인) 에 필수
#   android : activity / mActivity 접근용
#   Pillow  : 제외 (빌드 시간 단축)
# ============================================




# ============================================
# 화면
# ============================================

orientation = landscape

fullscreen = 0


# ============================================
# 안드로이드
# ============================================

# 저장소 접근 권한
#   MANAGE_EXTERNAL_STORAGE : Android 11+ 에서 Download 직접 읽기
#   READ/WRITE              : Android 10 이하 호환
#   (쉼표 뒤 공백 없이 작성)
android.permissions = MANAGE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# 타깃 API
android.api = 33
android.minapi = 24

android.ndk = 25b

# 먼저 arm64 단독으로 빌드 → 태블릿 설치 확인
# 설치가 거부되면 armeabi-v7a 를 추가 (빌드 시간 약 2배)
android.archs = arm64-v8a

# 산출물 형식
android.release_artifact = apk
android.debug_artifact = apk

# 백업 허용
android.allow_backup = True

# AndroidX
android.enable_androidx = True

# 첫 빌드 시 SDK 라이선스 자동 동의 (없으면 프롬프트에서 멈춤)
android.accept_sdk_license = True

# p4a.branch 는 지정하지 않음
#   develop 브랜치는 매일 바뀌고 깨진 커밋이 올라와
#   "어제 성공 / 오늘 실패" 가 발생함.
#   미지정 시 buildozer 1.5.0 이 검증된 안정 릴리스를 사용.
requirements = python3,,kivy==2.3.0,pyjnius,android

# ============================================
# 로그
# ============================================

[buildozer]

log_level = 2

warn_on_root = 1