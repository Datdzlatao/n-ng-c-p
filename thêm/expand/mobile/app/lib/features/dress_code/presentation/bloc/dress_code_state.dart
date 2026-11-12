import 'package:equatable/equatable.dart';
import '../../domain/entities/dress_code_result_entity.dart';

abstract class DressCodeState extends Equatable {
  const DressCodeState();
  @override
  List<Object?> get props => [];
}

class DressCodeInitial extends DressCodeState {}
class DressCodeLoading extends DressCodeState {}

class DressCodeChecked extends DressCodeState {
  final DressCodeResultEntity result;
  const DressCodeChecked(this.result);
  @override
  List<Object> get props => [result];
}

class DressCodeError extends DressCodeState {
  final String message;
  const DressCodeError(this.message);
  @override
  List<Object> get props => [message];
}
