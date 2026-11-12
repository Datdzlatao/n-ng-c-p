import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

// Mocks
abstract class QrState {}
class QrInitial extends QrState {}
class QrLoading extends QrState {}
class QrScanSuccess extends QrState { final String data; QrScanSuccess(this.data); }
class QrError extends QrState { final String message; QrError(this.message); }
class QrBloc extends Bloc<dynamic, QrState> { QrBloc() : super(QrInitial()); }

class QrScannerPage extends StatefulWidget {
  const QrScannerPage({super.key});

  @override
  State<QrScannerPage> createState() => _QrScannerPageState();
}

class _QrScannerPageState extends State<QrScannerPage> with SingleTickerProviderStateMixin {
  bool _scanned = false;
  late MobileScannerController controller;

  @override
  void initState() {
    super.initState();
    controller = MobileScannerController();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text('Quét Mã QR Điểm Danh', style: TextStyle(color: Colors.white)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      extendBodyBehindAppBar: true,
      body: BlocConsumer<QrBloc, QrState>(
        listener: (context, state) {
          if (state is QrScanSuccess) {
            showDialog(
              context: context,
              builder: (ctx) => AlertDialog(
                title: const Text('Thành công'),
                content: const Text('Điểm danh thành công!'),
                actions: [
                  TextButton(
                    onPressed: () {
                      Navigator.pop(ctx);
                      Navigator.pop(context, state.data);
                    },
                    child: const Text('Đóng'),
                  )
                ],
              ),
            );
          } else if (state is QrError) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(state.message)));
            setState(() { _scanned = false; });
          }
        },
        builder: (context, state) {
          return Stack(
            children: [
              MobileScanner(
                controller: controller,
                onDetect: (capture) {
                  if (!_scanned) {
                    final List<Barcode> barcodes = capture.barcodes;
                    if (barcodes.isNotEmpty) {
                      setState(() { _scanned = true; });
                      // context.read<QrBloc>().add(QrScanned(barcodes.first.rawValue));
                    }
                  }
                },
              ),
              // Overlay
              Container(
                decoration: ShapeDecoration(
                  shape: QrScannerOverlayShape(
                    borderColor: const Color(0xFF6366F1),
                    borderRadius: 10,
                    borderLength: 30,
                    borderWidth: 10,
                    cutOutSize: 300,
                  ),
                ),
              ).animate(onPlay: (controller) => controller.repeat(reverse: true)).fade(duration: 1.seconds, begin: 0.5, end: 1.0),
              
              if (state is QrLoading)
                const Center(child: CircularProgressIndicator(color: Colors.white)),
                
              const Positioned(
                bottom: 50,
                left: 0,
                right: 0,
                child: Center(
                  child: Text(
                    'Hướng camera vào mã QR của giáo viên',
                    style: TextStyle(color: Colors.white, fontSize: 16),
                  ),
                ),
              )
            ],
          );
        },
      ),
    );
  }
}

class QrScannerOverlayShape extends ShapeBorder {
  final Color borderColor;
  final double borderWidth;
  final double borderRadius;
  final double borderLength;
  final double cutOutSize;

  QrScannerOverlayShape({
    this.borderColor = Colors.red,
    this.borderWidth = 3.0,
    this.borderRadius = 0,
    this.borderLength = 40,
    this.cutOutSize = 250,
  });

  @override
  EdgeInsetsGeometry get dimensions => const EdgeInsets.all(10);

  @override
  Path getInnerPath(Rect rect, {TextDirection? textDirection}) {
    return Path()..fillType = PathFillType.evenOdd..addPath(getOuterPath(rect), Offset.zero);
  }

  @override
  Path getOuterPath(Rect rect, {TextDirection? textDirection}) {
    Path _getLeftTopPath(Rect rect) {
      return Path()
        ..moveTo(rect.left, rect.bottom)
        ..lineTo(rect.left, rect.top)
        ..lineTo(rect.right, rect.top);
    }
    return _getLeftTopPath(rect)
      ..lineTo(rect.right, rect.bottom)
      ..lineTo(rect.left, rect.bottom)
      ..lineTo(rect.left, rect.top);
  }

  @override
  void paint(Canvas canvas, Rect rect, {TextDirection? textDirection}) {
    // Basic implementation for custom overlay
    final width = rect.width;
    final height = rect.height;
    final borderOffset = borderWidth / 2;
    final double cutOutWidth = cutOutSize;
    final double cutOutHeight = cutOutSize;
    final _borderPaint = Paint()
      ..color = borderColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = borderWidth;
    final _boxPaint = Paint()
      ..color = Colors.black54
      ..style = PaintingStyle.fill
      ..blendMode = BlendMode.dstOut;
    
    final cutOutRect = Rect.fromCenter(
      center: rect.center,
      width: cutOutWidth,
      height: cutOutHeight,
    );
    canvas.drawRect(cutOutRect, _boxPaint);
    
    // Draw corners...
    canvas.drawRRect(
      RRect.fromRectAndRadius(cutOutRect, Radius.circular(borderRadius)),
      _borderPaint,
    );
  }

  @override
  ShapeBorder scale(double t) => this;
}
