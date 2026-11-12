import 'package:flutter_bloc/flutter_bloc.dart';
import '../../domain/usecases/mark_attendance_usecase.dart';
import '../../domain/usecases/get_attendance_history_usecase.dart';
import '../../domain/usecases/sync_offline_attendance_usecase.dart';
import 'attendance_event.dart';
import 'attendance_state.dart';

class AttendanceBloc extends Bloc<AttendanceEvent, AttendanceState> {
  final MarkAttendanceUseCase markAttendanceUseCase;
  final GetAttendanceHistoryUseCase getAttendanceHistoryUseCase;
  final SyncOfflineAttendanceUseCase syncOfflineUseCase;

  AttendanceBloc({
    required this.markAttendanceUseCase,
    required this.getAttendanceHistoryUseCase,
    required this.syncOfflineUseCase,
  }) : super(AttendanceInitial()) {
    on<MarkAttendanceRequested>(_onMark);
    on<LoadAttendanceHistory>(_onLoadHistory);
    on<SyncOfflineRequested>(_onSync);
  }

  Future<void> _onMark(MarkAttendanceRequested event, Emitter<AttendanceState> emit) async {
    emit(AttendanceLoading());
    final result = await markAttendanceUseCase(event.attendance);
    result.fold(
      (f) => emit(AttendanceError(f.message)),
      (_) => emit(AttendanceMarked(event.attendance)),
    );
  }

  Future<void> _onLoadHistory(LoadAttendanceHistory event, Emitter<AttendanceState> emit) async {
    emit(AttendanceLoading());
    final result = await getAttendanceHistoryUseCase(
      studentId: event.studentId,
      classId: event.classId,
    );
    result.fold(
      (f) => emit(AttendanceError(f.message)),
      (list) => emit(AttendanceHistoryLoaded(list)),
    );
  }

  Future<void> _onSync(SyncOfflineRequested event, Emitter<AttendanceState> emit) async {
    final result = await syncOfflineUseCase();
    result.fold((f) => null, (_) => emit(AttendanceSynced()));
  }
}
