import csv
import aiohttp
import asyncio
import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import webbrowser
from datetime import datetime
import time

async def get_video_title(session, api_key, video_id):
    if not video_id:
        return "N/A"
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {'part': 'snippet', 'id': video_id, 'key': api_key}
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            if data.get('items'):
                return data['items'][0]['snippet']['title']
    except aiohttp.ClientError as e:
        print(f"Error fetching video title: {e}")
    return "N/A"

async def get_comment_details(session, api_key, comment_id):
    try:
        url = "https://www.googleapis.com/youtube/v3/comments"
        params = {'part': 'snippet', 'id': comment_id, 'key': api_key}
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

        if not data.get('items'):
            return None

        comment_data = data['items'][0]['snippet']
        video_id = comment_data.get('videoId')

        if not video_id:
            parent_id = comment_data.get('parentId')
            if parent_id:
                parent_details = await get_comment_details(session, api_key, parent_id)
                if parent_details:
                    video_id = parent_details.get('videoId')

        video_title = await get_video_title(session, api_key, video_id)

        return {
            "comment_id": comment_id,
            "text": comment_data.get('textDisplay', 'N/A'),
            "video_title": video_title,
            "like_count": comment_data.get('likeCount', 0),
            "videoId": video_id
        }
    except aiohttp.ClientError:
        return None

async def get_comment_thread_details(session, api_key, comment_id):
    try:
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {'part': 'snippet,replies', 'id': comment_id, 'key': api_key}
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

        if not data.get('items'):
            details = await get_comment_details(session, api_key, comment_id)
            if details:
                details["is_reply"] = True
                details["reply_count"] = 0
                return details
            return None

        thread_data = data['items'][0]['snippet']
        top_level_comment = thread_data['topLevelComment']['snippet']
        video_id = top_level_comment.get('videoId')
        video_title = await get_video_title(session, api_key, video_id)

        return {
            "comment_id": comment_id,
            "text": top_level_comment.get('textDisplay', 'N/A'),
            "video_title": video_title,
            "like_count": top_level_comment.get('likeCount', 0),
            "reply_count": thread_data.get('totalReplyCount', 0),
            "is_reply": False,
            "videoId": video_id
        }
    except aiohttp.ClientError:
        return None

class YouTubeAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Comment Analyzer")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')

        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')
        self.style.configure("TProgressbar", thickness=20)

        self.file_paths = []
        self.processed_comments = []
        self.skipped_comments = []
        self.oldest_comment = None
        self.total_comments_to_process = 0

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)

        self.select_files_button = ttk.Button(buttons_frame, text="Select CSV Files", command=self.select_files)
        self.select_files_button.pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(buttons_frame, text="Start Processing", command=self.start_processing_thread)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.files_label = ttk.Label(main_frame, text="No files selected.", anchor="w", foreground="#555")
        self.files_label.pack(fill=tk.X, pady=5)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, expand=True)
        self.progress_label = ttk.Label(progress_frame, text="Progress: 0% (0/0) | ETA: --:--", anchor="center")
        self.progress_label.pack(fill=tk.X, pady=5)

        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(results_frame, text="Results:").pack(anchor="w")
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, height=10, bg="#ffffff", relief=tk.SUNKEN, borderwidth=1)
        self.results_text.pack(fill=tk.BOTH, expand=True)

    def select_files(self):
        self.file_paths = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if self.file_paths:
            self.get_total_comments()
            self.files_label.config(text=f"{len(self.file_paths)} file(s) selected ({self.total_comments_to_process} comments).")
        else:
            self.files_label.config(text="No files selected.")
    
    def get_total_comments(self):
        self.total_comments_to_process = 0
        for file_path in self.file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.total_comments_to_process += sum(1 for row in csv.reader(f) if row)
            except Exception as e:
                print(f"Could not count lines in {file_path}: {e}")

    def _update_results_safely(self, text):
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)

    def update_results(self, text):
        self.root.after(0, self._update_results_safely, text)
    
    def _update_progress_safely(self, value, text):
        self.progress_bar['value'] = value
        self.progress_label['text'] = text
    
    def update_progress(self, value, text):
        self.root.after(0, self._update_progress_safely, value, text)

    def start_processing_thread(self):
        if not self.file_paths:
            messagebox.showerror("Error", "Please select at least one CSV file.")
            return

        self.start_button.config(state=tk.DISABLED)
        self.results_text.delete('1.0', tk.END)
        self.processed_comments = []
        self.skipped_comments = []
        self.oldest_comment = None
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = self.total_comments_to_process
        self.progress_label['text'] = f"Progress: 0% (0/{self.total_comments_to_process}) | ETA: --:--"

        self.update_results("Starting processing...")

        thread = threading.Thread(target=self.run_async_processing, args=(self.process_files, self.handle_initial_completion))
        thread.daemon = True
        thread.start()

    def run_async_processing(self, async_func, completion_callback):
        try:
            asyncio.run(async_func())
        except Exception as e:
            self.update_results(f"\nAn unexpected error occurred in the async runner: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        finally:
            self.root.after(0, completion_callback)

    def handle_initial_completion(self):
        if self.skipped_comments:
            user_choice = messagebox.askyesno("Re-check Skipped Comments",
                                              f"{len(self.skipped_comments)} comments were skipped. Would you like to try processing them again?")
            if user_choice:
                self.start_recheck_thread()
            else:
                self.start_button.config(state=tk.NORMAL)
                if self.processed_comments:
                    self.show_stats_window()
        else:
            self.start_button.config(state=tk.NORMAL)
            if self.processed_comments:
                self.show_stats_window()

    def start_recheck_thread(self):
        self.start_button.config(state=tk.DISABLED)
        total_skipped = len(self.skipped_comments)
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = total_skipped
        self.progress_label['text'] = f"Progress: 0% (0/{total_skipped}) | ETA: --:--"
        self.update_results("\n--- Re-checking skipped comments... ---")
        
        thread = threading.Thread(target=self.run_async_processing, args=(self.reprocess_skipped, self.handle_final_completion))
        thread.daemon = True
        thread.start()

    def handle_final_completion(self):
        self.start_button.config(state=tk.NORMAL)
        if self.processed_comments:
            self.show_stats_window()

    async def _process_comment_list(self, comment_list, is_recheck=False):
        api_key = "ENTER-YOUR-GOOGLE-API-KEY-HERE"
        comments_processed_count = 0
        start_time = time.time()
        
        if is_recheck:
            newly_skipped = []
            total_to_process = len(comment_list)
        else:
            total_to_process = self.total_comments_to_process


        async with aiohttp.ClientSession() as session:
            for row in comment_list:
                if not row or len(row) < 2:
                    continue
                
                comments_processed_count += 1
                entry = row[0].strip()
                timestamp_str = row[1].strip()
                comment_id = None
                
                if 'youtube.com' in entry:
                    try:
                        if '&lc=' in entry: comment_id = entry.split('&lc=')[1].split('&')[0]
                        elif '?lc=' in entry: comment_id = entry.split('?lc=')[1].split('&')[0]
                    except IndexError: pass
                elif re.match(r'^[A-Za-z0-9_.]{20,}$', entry):
                    comment_id = entry

                if not comment_id:
                    self.update_results(f"Skipping invalid entry: {entry}")
                    if is_recheck: newly_skipped.append(row)
                    else: self.skipped_comments.append(row)
                    continue
                
                details = await get_comment_thread_details(session, api_key, comment_id)

                if details:
                    details['timestamp'] = timestamp_str
                    self.processed_comments.append(details)
                    try:
                        current_timestamp = datetime.fromisoformat(timestamp_str)
                        if self.oldest_comment is None or current_timestamp < datetime.fromisoformat(self.oldest_comment['timestamp']):
                            self.oldest_comment = details
                    except (ValueError, TypeError):
                        self.update_results(f"Warning: Could not parse timestamp '{timestamp_str}'")
                    self.update_results(f"Processed: {details['video_title']} (Likes: {details['like_count']})")
                else:
                    self.update_results(f"Skipping comment ID: {comment_id}")
                    if is_recheck: newly_skipped.append(row)
                    else: self.skipped_comments.append(row)
                
                elapsed_time = time.time() - start_time
                percent_done = (comments_processed_count / total_to_process) * 100
                if comments_processed_count > 0:
                    avg_time_per_comment = elapsed_time / comments_processed_count
                    remaining_comments = total_to_process - comments_processed_count
                    eta_seconds = int(avg_time_per_comment * remaining_comments)
                    eta_str = time.strftime('%M:%S', time.gmtime(eta_seconds))
                else: eta_str = "--:--"
                
                progress_text = f"Progress: {percent_done:.1f}% ({comments_processed_count}/{total_to_process}) | ETA: {eta_str}"
                self.update_progress(comments_processed_count, progress_text)

        if is_recheck:
            self.skipped_comments = newly_skipped

    async def process_files(self):
        all_rows = []
        for file_path in self.file_paths:
            self.update_results(f"\n--- Reading File: {os.path.basename(file_path)} ---\n")
            try:
                with open(file_path, mode='r', encoding='utf-8') as infile:
                    reader = csv.reader(infile)
                    all_rows.extend([row for row in reader if row])
            except Exception as e:
                self.update_results(f"An error occurred reading {os.path.basename(file_path)}: {e}")

        await self._process_comment_list(all_rows, is_recheck=False)
        self.update_results("\n--- Initial Processing Complete ---")

    async def reprocess_skipped(self):
        await self._process_comment_list(list(self.skipped_comments), is_recheck=True)
        self.update_results("\n--- Re-check Complete ---")

    def show_stats_window(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Comment Statistics")
        stats_window.geometry("700x650")
        stats_window.configure(bg='#f0f0f0')

        most_liked = max(self.processed_comments, key=lambda x: x['like_count'])
        most_replied = max(self.processed_comments, key=lambda x: x.get('reply_count', 0))

        main_stats_frame = ttk.Frame(stats_window, padding="15")
        main_stats_frame.pack(fill=tk.BOTH, expand=True)

        general_frame = ttk.LabelFrame(main_stats_frame, text="Overall Stats", padding="10")
        general_frame.pack(fill=tk.X, pady=(0,15))
        ttk.Label(general_frame, text=f"Total Comments Processed: {len(self.processed_comments)}", font=("Helvetica", 12, "bold")).pack(anchor='w')

        liked_frame = ttk.LabelFrame(main_stats_frame, text="Most Liked Comment", padding="10")
        liked_frame.pack(fill=tk.X, pady=5)
        ttk.Label(liked_frame, text=f"Likes: {most_liked['like_count']}", font=("Helvetica", 12, "bold")).pack(anchor='w')
        ttk.Label(liked_frame, text=f"Video: {most_liked['video_title']}", wraplength=650).pack(anchor='w', pady=2)
        ttk.Label(liked_frame, text=f"Comment: {most_liked['text']}", wraplength=650).pack(anchor='w', pady=2)
        url_liked = f"https://www.youtube.com/watch?v={most_liked.get('videoId', '')}&lc={most_liked['comment_id']}"
        ttk.Button(liked_frame, text="Open Comment", command=lambda: webbrowser.open_new_tab(url_liked)).pack(pady=5)

        replied_frame = ttk.LabelFrame(main_stats_frame, text="Most Replied-To Comment", padding="10")
        replied_frame.pack(fill=tk.X, pady=5)
        ttk.Label(replied_frame, text=f"Replies: {most_replied.get('reply_count', 0)}", font=("Helvetica", 12, "bold")).pack(anchor='w')
        ttk.Label(replied_frame, text=f"Video: {most_replied['video_title']}", wraplength=650).pack(anchor='w', pady=2)
        ttk.Label(replied_frame, text=f"Comment: {most_replied['text']}", wraplength=650).pack(anchor='w', pady=2)
        url_replied = f"https://www.youtube.com/watch?v={most_replied.get('videoId', '')}&lc={most_replied['comment_id']}"
        ttk.Button(replied_frame, text="Open Comment", command=lambda: webbrowser.open_new_tab(url_replied)).pack(pady=5)

        if self.oldest_comment:
            oldest_frame = ttk.LabelFrame(main_stats_frame, text="Oldest Comment", padding="10")
            oldest_frame.pack(fill=tk.X, pady=5)
            
            try:
                ts_obj = datetime.fromisoformat(self.oldest_comment['timestamp'])
                ts_display = ts_obj.strftime("%B %d, %Y at %I:%M %p")
                ttk.Label(oldest_frame, text=f"Date: {ts_display}", font=("Helvetica", 12, "bold")).pack(anchor='w')
            except (ValueError, TypeError):
                 ttk.Label(oldest_frame, text=f"Date: {self.oldest_comment['timestamp']}", font=("Helvetica", 12, "bold")).pack(anchor='w')

            ttk.Label(oldest_frame, text=f"Video: {self.oldest_comment['video_title']}", wraplength=650).pack(anchor='w', pady=2)
            ttk.Label(oldest_frame, text=f"Comment: {self.oldest_comment['text']}", wraplength=650).pack(anchor='w', pady=2)
            url_oldest = f"https://www.youtube.com/watch?v={self.oldest_comment.get('videoId', '')}&lc={self.oldest_comment['comment_id']}"
            ttk.Button(oldest_frame, text="Open Comment", command=lambda: webbrowser.open_new_tab(url_oldest)).pack(pady=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeAnalyzerApp(root)
    root.mainloop()
