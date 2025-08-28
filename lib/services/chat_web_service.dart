import 'dart:async';
import 'dart:convert';
import 'package:web_socket_client/web_socket_client.dart';
import 'package:flutter/foundation.dart' show kIsWeb, kDebugMode;

class ChatWebService {
  static final _instance = ChatWebService._internal();
  WebSocket? _socket;

  factory ChatWebService() => _instance;

  ChatWebService._internal();
  final _searchResultController = StreamController<Map<String, dynamic>>();
  final _contentController = StreamController<Map<String, dynamic>>();

  Stream<Map<String, dynamic>> get searchResultStream =>
      _searchResultController.stream;
  Stream<Map<String, dynamic>> get contentStream => _contentController.stream;

  String get websocketUrl {
    // Use your actual Render deployment URL
    const renderUrl = 'wss://perplexity-clone-backend.onrender.com/ws/chat';
    const localUrl = 'ws://localhost:8000/ws/chat';
    
    // Use local URL in debug mode, Render URL in production
    if (kDebugMode) {
      return localUrl;
    }
    return renderUrl;
  }

  void connect() {
    try {
      _socket = WebSocket(Uri.parse(websocketUrl));

      _socket!.connection.listen(
        (_) => print('WebSocket connected'),
        onError: (error) => print('WebSocket connection error: $error'),
      );

      _socket!.messages.listen(
        (message) {
          try {
            final data = json.decode(message);
            if (data['type'] == 'search_result') {
              _searchResultController.add(data);
            } else if (data['type'] == 'content') {
              _contentController.add(data);
            } else if (data['type'] == 'ping') {
              // Handle keep-alive ping
              print('Received ping from server');
            }
          } catch (e) {
            print('Error parsing message: $e');
          }
        },
        onError: (error) => print('WebSocket message error: $error'),
        onDone: () {
          print('WebSocket connection closed');
          // Attempt to reconnect after a delay
          Future.delayed(Duration(seconds: 5), () => connect());
        },
      );
    } catch (e) {
      print('Failed to connect WebSocket: $e');
    }
  }

  void chat(String query) {
    if (_socket == null || _socket!.connection.state != ConnectionState.open) {
      print('WebSocket not connected, attempting to reconnect...');
      connect();
      // Wait a bit for connection to establish
      Future.delayed(Duration(seconds: 1), () => chat(query));
      return;
    }
    
    print('Sending query: $query');
    _socket!.send(json.encode({'query': query}));
  }

  void dispose() {
    _socket?.close();
    _searchResultController.close();
    _contentController.close();
  }
}