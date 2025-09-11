import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/status.dart' as status;

/// A production-grade WebSocket service for chat communication.
class ChatWebService {
  static final ChatWebService _instance = ChatWebService._internal();
  factory ChatWebService() => _instance;
  ChatWebService._internal();

  WebSocketChannel? _channel;
  Timer? _heartbeatTimer;
  Timer? _reconnectTimer;
  bool _isConnecting = false;
  bool _disposed = false;
  bool _connected = false;

  // Message queue for offline/reconnect scenarios (max 50 messages).
  final List<String> _messageQueue = [];
  static const int _maxQueueSize = 50;

  // Exponential backoff variables.
  int _reconnectAttempts = 0;

  // Streams for data.
  final _searchResultController = StreamController<Map<String, dynamic>>.broadcast();
  final _contentController = StreamController<Map<String, dynamic>>.broadcast();
  final _connectionStatusController = StreamController<bool>.broadcast();

  Stream<Map<String, dynamic>> get searchResultStream => _searchResultController.stream;
  Stream<Map<String, dynamic>> get contentStream => _contentController.stream;
  Stream<bool> get connectionStatusStream => _connectionStatusController.stream;

  /// Selects the WebSocket URL based on environment.
  String get websocketUrl {
    const renderUrl = String.fromEnvironment(
      'WS_RENDER_URL',
      defaultValue: 'wss://perplexity-clone-rrjo.onrender.com/ws/chat',
    );
    const localUrl = 'ws://localhost:8000/ws/chat';

    return kDebugMode ? localUrl : renderUrl;
  }

  bool get isConnected => _connected;

  /// Connect to the WebSocket server.
  void connect() {
    if (_isConnecting || isConnected || _disposed) return;

    _isConnecting = true;
    _log('Attempting to connect to: $websocketUrl');

    try {
      disconnect(); // close existing before reconnecting
      _channel = WebSocketChannel.connect(Uri.parse(websocketUrl));

      _channel!.stream.listen(
        (message) {
          _isConnecting = false;
          if (!_connected) {
            _connected = true;
            _connectionStatusController.add(true);
            _reconnectAttempts = 0;
            _log('✅ WebSocket connected successfully');
            _startHeartbeat();
            _flushMessageQueue();
          }

          try {
            final data = json.decode(message);
            _handleMessage(data);
          } catch (e) {
            _log('⚠️ Error parsing message: $e');
          }
        },
        onError: (error) {
          _log('❌ WebSocket connection error: $error');
          _isConnecting = false;
          _connected = false;
          _connectionStatusController.add(false);
          _scheduleReconnect();
        },
        onDone: () {
          _log('ℹ️ WebSocket connection closed');
          _isConnecting = false;
          _connected = false;
          _connectionStatusController.add(false);
          _stopHeartbeat();
          _scheduleReconnect();
        },
      );
    } catch (e) {
      _log('❌ Failed to connect WebSocket: $e');
      _isConnecting = false;
      _connected = false;
      _connectionStatusController.add(false);
      _scheduleReconnect();
    }
  }

  /// Handle server messages.
  void _handleMessage(Map<String, dynamic> data) {
    final messageType = data['type'];

    switch (messageType) {
      case 'search_result':
        _searchResultController.add(data);
        break;
      case 'content':
        _contentController.add(data);
        break;
      case 'start':
        _log('ℹ️ Starting new response stream');
        break;
      case 'end':
        _log('ℹ️ Response stream ended');
        break;
      case 'error':
        _log('❌ Server error: ${data['message']}');
        break;
      case 'ping':
        _log('↔️ Received ping from server');
        _sendPong();
        break;
      default:
        _log('❓ Unknown message type: $messageType');
    }
  }

  void _sendPong() {
    if (isConnected) {
      try {
        _channel!.sink.add(json.encode({'type': 'pong'}));
      } catch (e) {
        _log('❌ Failed to send pong: $e');
      }
    }
  }

  void _startHeartbeat() {
    _stopHeartbeat();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (!isConnected) {
        timer.cancel();
        return;
      }

      try {
        _channel!.sink.add(json.encode({'type': 'heartbeat'}));
      } catch (e) {
        _log('❌ Heartbeat failed: $e');
        timer.cancel();
        _scheduleReconnect();
      }
    });
  }

  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  void _scheduleReconnect() {
    if (_isConnecting || _disposed) return;

    final delay = min(30, pow(2, _reconnectAttempts).toInt());
    _reconnectAttempts++;
    _log('⏳ Scheduling reconnection in $delay seconds...');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: delay), () {
      if (!isConnected && !_isConnecting && !_disposed) {
        connect();
      }
    });
  }

  void chat(String query) {
    if (_disposed) {
      _log('⚠️ ChatWebService disposed, cannot send message');
      return;
    }

    if (query.trim().isEmpty) {
      _log('⚠️ Empty query, not sending');
      return;
    }

    final message = json.encode({'query': query.trim()});

    if (!isConnected) {
      _log('⚠️ Not connected, queueing message and reconnecting...');
      _queueMessage(message);
      if (!_isConnecting) connect();
      return;
    }

    try {
      _log('➡️ Sending query: ${query.substring(0, query.length.clamp(0, 50))}...');
      _channel!.sink.add(message);
    } catch (e) {
      _log('❌ Failed to send message: $e');
      _queueMessage(message);
      _scheduleReconnect();
    }
  }

  void _queueMessage(String message) {
    if (_messageQueue.length >= _maxQueueSize) {
      _messageQueue.removeAt(0); // drop oldest
    }
    _messageQueue.add(message);
  }

  void _flushMessageQueue() {
    for (final msg in _messageQueue) {
      try {
        _channel?.sink.add(msg);
      } catch (e) {
        _log('❌ Failed to flush message: $e');
      }
    }
    _messageQueue.clear();
  }

  void disconnect() {
    if (_disposed) return;
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    _channel?.sink.close(status.normalClosure);
    _channel = null;
    _connected = false;
    if (!_connectionStatusController.isClosed) {
      _connectionStatusController.add(false);
    }
  }

  void dispose() {
    if (_disposed) return;
    _disposed = true;

    _log('🛑 Disposing ChatWebService...');
    disconnect();
    _messageQueue.clear();

    if (!_searchResultController.isClosed) _searchResultController.close();
    if (!_contentController.isClosed) _contentController.close();
    if (!_connectionStatusController.isClosed) _connectionStatusController.close();
  }

  void _log(String message) {
    debugPrint('[ChatWebService] $message');
  }
}
