import 'package:equatable/equatable.dart';
import 'package:image/image.dart' as img;

abstract class DressCodeEvent extends Equatable {
  const DressCodeEvent();
  @override
  List<Object?> get props => [];
}

class DressCodeCheckRequested extends DressCodeEvent {
  final img.Image image;
  const DressCodeCheckRequested(this.image);
  @override
  List<Object> get props => [image];
}

class DressCodeReset extends DressCodeEvent {}
