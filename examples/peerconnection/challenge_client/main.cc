/*
 *  Copyright 2012 The WebRTC Project Authors. All rights reserved.
 *
 *  Use of this source code is governed by a BSD-style license
 *  that can be found in the LICENSE file in the root of the source
 *  tree. An additional intellectual property rights grant can be found
 *  in the file PATENTS.  All contributing project authors may
 *  be found in the AUTHORS file in the root of the source tree.
 */

#include "conductor.h"
#include "defaults.h"
#include "logger.h"
#include "peer_connection_client.h"

#include "api/alphacc_config.h"
#include "rtc_base/ssl_adapter.h"
#include "rtc_base/string_utils.h"  // For ToUtf8
#include "system_wrappers/include/field_trial.h"

#include <chrono>
#include <functional>
#include <future>
#include <iostream>
#include <fstream>
#include <memory>
#include <thread>

#include <errno.h>
#include <stdio.h>
#include <stdexcept>
#include <string.h>

class VideoRenderer : public rtc::VideoSinkInterface<webrtc::VideoFrame> {
 public:
  VideoRenderer(webrtc::VideoTrackInterface* track_to_render,
                MainWndCallback* callback)
      : track_(track_to_render), callback_(callback) {
    track_->AddOrUpdateSink(this, rtc::VideoSinkWants());
  }
  ~VideoRenderer() { track_->RemoveSink(this); }
  void OnFrame(const webrtc::VideoFrame& frame) {
    callback_->OnFrameCallback(frame);
  }

 private:
  rtc::scoped_refptr<webrtc::VideoTrackInterface> track_;
  MainWndCallback* callback_;
};

class MainWindowMock : public MainWindow {
 private:
  std::unique_ptr<VideoRenderer> remote_renderer_;
  MainWndCallback* callback_;
  std::shared_ptr<rtc::AutoSocketServerThread> socket_thread_;
  const webrtc::AlphaCCConfig* config_;
  int close_time_;
  int error_before_start_;

 public:
  MainWindowMock(std::shared_ptr<rtc::AutoSocketServerThread> socket_thread)
      : callback_(NULL),
        socket_thread_(socket_thread),
        config_(webrtc::GetAlphaCCConfig()),
        close_time_(rtc::Thread::kForever),
        error_before_start_(0) {}
  void RegisterObserver(MainWndCallback* callback) override {
    callback_ = callback;
  }

  bool IsWindow() override { return true; }

  void MessageBox(const char* caption,
                  const char* text,
                  bool is_error) override {
    RTC_LOG(LS_INFO) << caption << ": " << text;
  }

  UI current_ui() override { return WAIT_FOR_CONNECTION; }

  void SwitchToConnectUI() override {}
  void SwitchToStreamingUI() override {}

  void StartLocalRenderer(webrtc::VideoTrackInterface* local_video) override {}

  void StopLocalRenderer() override {}

  void StartRemoteRenderer(webrtc::VideoTrackInterface* remote_video) override {
    remote_renderer_.reset(new VideoRenderer(remote_video, callback_));
  }

  void StopRemoteRenderer() override { remote_renderer_.reset(); }

  void QueueUIThreadCallback(int msg_id, void* data) override {
    callback_->UIThreadCallback(msg_id, data);
  }

  void Run() {
    if (error_before_start_ != 0) {
      RTC_LOG(LS_INFO) << "SetErrorBeforeStartSignal called. Won't run wnd.Run()";
      return;
    }

    if (config_->conn_autoclose != kAutoCloseDisableValue) {
      while (close_time_ == rtc::Thread::kForever) {
        RTC_CHECK(socket_thread_->ProcessMessages(0));
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
      }
      RTC_CHECK(socket_thread_->ProcessMessages(close_time_));
    } else {
      socket_thread_->Run();
    }
    StopRemoteRenderer();
    socket_thread_->Stop();
    callback_->Close();
  }

  void StartAutoCloseTimer(int close_time) override {
    close_time_ = close_time;
  }

  void SetErrorBeforeStartSignal() {
    error_before_start_ = 1;
  }
};

int get_port(const std::string port_path) {
  int port = 8000;
  std::string line;
  std::ifstream port_file(port_path);
  std::getline(port_file, line);
  std::stringstream sss(line);
  if( !( sss >> port ) ) {
      std::cerr << "Failed to read port " << line << " to int" << std::endl;
  } else {
      std::cout << "Read port " << port << std::endl;
  }
  port_file.close();

  return port;
}

int main(int argc, char* argv[]) {
  const auto json_file_path = argv[1];
  if (!webrtc::ParseAlphaCCConfig(json_file_path)) {
    std::cerr << "Error in parsing config file " << json_file_path << std::endl;
    exit(EINVAL);
  }
  const std::string dest_ip = argv[2];
  const std::string port_path = argv[3];
  int assigned_port = get_port(port_path);
  const std::string log_output_path = argv[4];

  rtc::LogMessage::LogToDebug(rtc::LS_INFO);

  rtc::PhysicalSocketServer socket_server;
  std::shared_ptr<rtc::AutoSocketServerThread> thread(
      new rtc::AutoSocketServerThread(&socket_server));
  MainWindowMock wnd(thread);
  rtc::InitializeSSL();
  PeerConnectionClient client;
  rtc::scoped_refptr<Conductor> conductor(
      new rtc::RefCountedObject<Conductor>(&client, &wnd));

  std::unique_ptr<FileLogSink> sink;
  sink = std::make_unique<FileLogSink>(log_output_path);

  auto config = webrtc::GetAlphaCCConfig();
  if (config->is_receiver) {
    auto ret = client.StartListen(config->listening_ip, assigned_port);
    if (ret < 0) {
      RTC_LOG(LS_INFO) << "Receiver: StartListen() finished with error, terminating";
      wnd.SetErrorBeforeStartSignal();
    }
  } else if (config->is_sender) {
    auto ret = client.StartConnect(dest_ip, assigned_port);
    if (ret < 0) {
      RTC_LOG(LS_INFO) << "Sender: StartConnect() finished with error, terminating";
      wnd.SetErrorBeforeStartSignal();
    }
  }

  wnd.Run();
  rtc::CleanupSSL();
  return 0;
}