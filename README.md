# My-YT-Comment-Tool

A user-friendly desktop application that processes your exported YouTube comment history from Google Takeout. It fetches up-to-date statistics like likes and replies, then displays your most popular and oldest comments with direct links.

---

## Features

-   **Easy to Use GUI:** A simple graphical interface, no command-line needed.
-   **Bulk CSV Processing:** Select and process multiple CSV files at once.
-   **Live Stats:** Fetches current like and reply counts for each comment.
-   **Detailed Progress:** A real-time progress bar shows the status, item count, and an ETA.
-   **Intelligent Error Handling:** Retries comments that fail on the first pass.
-   **Comprehensive Report:** Generates a final report highlighting:
    -   Your most-liked comment.
    -   Your most-replied-to comment.
    -   Your oldest comment.
-   **Clickable Links:** Instantly open any of the top comments in your web browser.

---

## How to Use

Follow these steps to get your YouTube comment stats.

### Step 1: Get Your Comments from Google Takeout

You need to export your YouTube comment history before using this tool.

1.  Go to the [Google Takeout](https://takeout.google.com/) website.
2.  Under "Create a new export," click **Deselect all**.
3.  Scroll down to find **YouTube and YouTube Music** and check the box next to it.
4.  Click the **All YouTube data included** button.
5.  In the pop-up, click **Deselect all**, then check the box only for **comments**. Click **OK**.
6.  Scroll to the bottom and click **Next step**.
7.  Choose your preferred delivery method (e.g., "Send download link via email") and file type (`.zip`). Click **Create export**.
8.  Google will notify you when your export is ready. Download the `.zip` file and extract it. Inside, you will find your `comments.csv` file located in the `Takeout/YouTube and YouTube Music/my-comments/` directory.

### Step 2: Prepare the Application

1.  **Clone or Download this Repository:**
    ```bash
    git clone https://github.com/Gh0styTongue/My-YT-Comment-Tool.git
    cd My-YT-Comment-Tool
    ```
2.  **Install Dependencies:**
    This script uses the `aiohttp` library. You can install it using pip.
    ```bash
    pip install aiohttp
    ```

### Step 3: Run the Tool

1.  **Run the Python script:**
    ```bash
    python com.py
    ```
    (Replace `com.py` with the actual name of the Python file).
2.  **Select Your CSV Files:** Click the "Select CSV Files" button and choose the `comments.csv` file(s) you downloaded from Google Takeout.
3.  **Start Processing:** Click the "Start Processing" button to begin fetching the data.
4.  **View Results:** Watch the progress in the main window. Once complete, a new window will appear with your top comment statistics.

---

## Disclaimer

This application uses a hardcoded API key for accessing the YouTube Data API. Please be aware of the following:

-   **Quota Limits:** The YouTube Data API has a daily usage quota. Processing a very large number of comments may temporarily exhaust this quota.
-   **API Key Usage:** The provided API key is for demonstration purposes. For heavy use, it is recommended to generate and use your own key from the [Google Cloud Console](https://console.cloud.google.com/).
