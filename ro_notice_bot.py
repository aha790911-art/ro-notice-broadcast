name: Check RO Notice

on:
  schedule:
    # 設定為每 5 分鐘檢查一次（GitHub Actions 支援的最短週期）
    - cron: '*/5 * * * *'
  workflow_dispatch: # 支援網頁上手動按鈕觸發

# 防重複鎖定：確保同一時間永遠只有一個檢查任務在執行
concurrency:
  group: ro-notice-broadcast
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  run-crawler:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          pip install requests beautifulsoup4 playwright
          playwright install --with-deps chromium

      - name: Run Notice Crawler
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: |
          python ro_notice_bot.py

      - name: Commit and Push State
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add last_notice_id.txt
          if git diff --staged --quiet; then
            echo "無新公告，略過存檔"
          else
            git commit -m "chore: 更新最新公告 ID"
            git push
          fi
